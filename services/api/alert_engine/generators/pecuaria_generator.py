from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from pecuaria.animal.models import LoteAnimal
from pecuaria.schemas.lote_indicadores_schema import LoteIndicadoresResponse
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService
from campo.models import TarefaCampo


@dataclass(slots=True)
class PecuariaAlertGenerationResult:
    lotes_sem_pesagem: int = 0
    vacinacoes_atrasadas: int = 0
    custos_sanitarios_altos: int = 0

    @property
    def total_alertas(self) -> int:
        return self.lotes_sem_pesagem + self.vacinacoes_atrasadas + self.custos_sanitarios_altos


class PecuariaAlertGenerator:
    """Generates canonical livestock alerts from existing pecuaria signals."""

    ACTION_URL_LOTE = "/dashboard/pecuaria/lotes"
    ACTION_URL_MANEJO = "/dashboard/pecuaria/manejo"

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def gerar_alertas_pecuaria(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
        dias_sem_pesagem: int = 45,
        limite_custo_sanitario_por_cabeca: float = 50.0,
    ) -> PecuariaAlertGenerationResult:
        """Scan livestock data and materialize canonical alerts.

        Args:
            unidade_produtiva_id: Optional production-unit scope.
            dias_sem_pesagem: Threshold in days to flag missing recent weighing.
            limite_custo_sanitario_por_cabeca: Threshold for per-head sanitary cost alerts.

        Returns:
            Counters for each alert family generated in this run.
        """
        await self._set_rls_context()
        result = PecuariaAlertGenerationResult()
        for lote in await self._lotes_ativos(unidade_produtiva_id):
            resumo = await self._resumo_lote(lote.id)
            if self._deve_alertar_pesagem(resumo, dias_sem_pesagem):
                await self._emitir_alerta_sem_pesagem(lote, resumo, dias_sem_pesagem)
                result.lotes_sem_pesagem += 1
            if self._deve_alertar_custo(resumo, limite_custo_sanitario_por_cabeca):
                await self._emitir_alerta_custo_sanitario(lote, resumo, limite_custo_sanitario_por_cabeca)
                result.custos_sanitarios_altos += 1
        for tarefa in await self._vacinacoes_atrasadas(unidade_produtiva_id):
            await self._emitir_alerta_vacinacao_atrasada(tarefa)
            result.vacinacoes_atrasadas += 1
        return result

    async def _emitir_alerta_sem_pesagem(
        self,
        lote: LoteAnimal,
        resumo: LoteIndicadoresResponse,
        dias_sem_pesagem: int,
    ) -> None:
        ultima = resumo.ultima_pesagem.isoformat() if resumo.ultima_pesagem else "sem pesagem registrada"
        await self._create_alert(
            title="Lote sem pesagem recente",
            message=(
                f"O lote '{lote.identificacao}' possui {resumo.quantidade_animais} animais ativos "
                f"e está sem pesagem recente. Última pesagem: {ultima}."
            ),
            severity=Severity.WARNING,
            priority=Priority.HIGH,
            trigger_type=TriggerType.RULE,
            source_type="PECUARIA_LOTE_SEM_PESAGEM",
            source_id=str(lote.id),
            dedupe_key=f"pecuaria:lote_sem_pesagem:{lote.id}",
            action_label="Ver lote",
            action_url=self.ACTION_URL_LOTE,
            unidade_produtiva_id=lote.unidade_produtiva_id,
            context={
                "lote_id": str(lote.id),
                "lote_identificacao": lote.identificacao,
                "quantidade_animais": resumo.quantidade_animais,
                "ultima_pesagem": ultima,
                "dias_sem_pesagem": dias_sem_pesagem,
            },
        )

    async def _emitir_alerta_vacinacao_atrasada(self, tarefa: TarefaCampo) -> None:
        await self._create_alert(
            title="Vacinação planejada atrasada",
            message=(
                f"A vacinação '{tarefa.titulo or tarefa.type}' do lote "
                f"{tarefa.lote_id} está atrasada desde {self._format_date(tarefa.data_programada)}."
            ),
            severity=Severity.CRITICAL,
            priority=Priority.URGENT,
            trigger_type=TriggerType.RULE,
            source_type="PECUARIA_VACINACAO_ATRASADA",
            source_id=str(tarefa.id),
            dedupe_key=f"pecuaria:vacinacao_atrasada:{tarefa.id}",
            action_label="Ver manejo",
            action_url=self.ACTION_URL_MANEJO,
            unidade_produtiva_id=tarefa.unidade_produtiva_id,
            context={
                "tarefa_campo_id": str(tarefa.id),
                "lote_id": str(tarefa.lote_id) if tarefa.lote_id else None,
                "data_programada": self._format_date(tarefa.data_programada),
                "status_execucao": tarefa.status_execucao,
            },
        )

    async def _emitir_alerta_custo_sanitario(
        self,
        lote: LoteAnimal,
        resumo: LoteIndicadoresResponse,
        limite_custo_sanitario_por_cabeca: float,
    ) -> None:
        await self._create_alert(
            title="Custo sanitário elevado",
            message=(
                f"O lote '{lote.identificacao}' está com custo sanitário por cabeça de "
                f"R$ {resumo.custo_sanitario_por_cabeca:.2f}, acima do limite de "
                f"R$ {limite_custo_sanitario_por_cabeca:.2f}."
            ),
            severity=Severity.WARNING,
            priority=Priority.NORMAL,
            trigger_type=TriggerType.THRESHOLD,
            source_type="PECUARIA_CUSTO_SANITARIO_ALTO",
            source_id=str(lote.id),
            dedupe_key=f"pecuaria:custo_sanitario_alto:{lote.id}",
            action_label="Ver lote",
            action_url=self.ACTION_URL_LOTE,
            unidade_produtiva_id=lote.unidade_produtiva_id,
            context={
                "lote_id": str(lote.id),
                "lote_identificacao": lote.identificacao,
                "quantidade_animais": resumo.quantidade_animais,
                "custo_sanitario_por_cabeca": float(resumo.custo_sanitario_por_cabeca),
                "limite_custo_sanitario_por_cabeca": limite_custo_sanitario_por_cabeca,
            },
        )

    async def _create_alert(
        self,
        *,
        title: str,
        message: str,
        severity: Severity,
        priority: Priority,
        trigger_type: TriggerType,
        source_type: str,
        source_id: str,
        dedupe_key: str,
        action_label: str,
        action_url: str,
        unidade_produtiva_id: uuid.UUID | None,
        context: dict[str, object],
    ) -> None:
        service = AlertLifecycleService(self.session, self.tenant_id)
        payload = OperationalAlertCreate(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=Domain.LIVESTOCK,
            category=self._category_for_source(source_type),
            title=title,
            message=message,
            severity=severity,
            priority=priority,
            status=AlertStatus.OPEN,
            trigger_type=trigger_type,
            source_type=source_type,
            source_id=source_id,
            source_event_ids=[],
            source_indicator_ids=[],
            dedupe_key=dedupe_key,
            action_label=action_label,
            action_url=action_url,
            context=context,
        )
        await service.create_or_update_alert(payload)

    async def _lotes_ativos(self, unidade_produtiva_id: uuid.UUID | None) -> list[LoteAnimal]:
        stmt = select(LoteAnimal).where(LoteAnimal.tenant_id == self.tenant_id, LoteAnimal.ativo == True)
        if unidade_produtiva_id is not None:
            stmt = stmt.where(LoteAnimal.unidade_produtiva_id == unidade_produtiva_id)
        rows = await self.session.execute(stmt.order_by(LoteAnimal.identificacao.asc()))
        return list(rows.scalars().all())

    async def _resumo_lote(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        return await LoteIndicadoresService(self.session, self.tenant_id).resumir(lote_id)

    async def _vacinacoes_atrasadas(self, unidade_produtiva_id: uuid.UUID | None) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == self.tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.type == "VACINACAO",
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada < date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        rows = await self.session.execute(stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc()))
        return list(rows.scalars().all())

    @staticmethod
    def _deve_alertar_pesagem(resumo: LoteIndicadoresResponse, dias_sem_pesagem: int) -> bool:
        if resumo.quantidade_animais <= 0:
            return False
        if resumo.ultima_pesagem is None:
            return True
        return (date.today() - resumo.ultima_pesagem).days > dias_sem_pesagem

    @staticmethod
    def _deve_alertar_custo(resumo: LoteIndicadoresResponse, limite: float) -> bool:
        return resumo.quantidade_animais > 0 and float(resumo.custo_sanitario_por_cabeca) > limite

    @staticmethod
    def _category_for_source(source_type: str) -> Category:
        if source_type == "PECUARIA_VACINACAO_ATRASADA":
            return Category.SANITARIO
        if source_type == "PECUARIA_CUSTO_SANITARIO_ALTO":
            return Category.ECONOMICO
        return Category.PRODUCAO

    async def _set_rls_context(self) -> None:
        await self.session.execute(text(f"SET LOCAL app.current_tenant_id = '{self.tenant_id}';"))

    @staticmethod
    def _format_date(value: date | None) -> str:
        return value.isoformat() if value else "sem data"
