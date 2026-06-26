from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from campo.models import TarefaCampo
from pecuaria.animal.models import LoteAnimal
from pecuaria.schemas.lote_indicadores_schema import LoteIndicadoresResponse
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService

from ._support import has_active_alert, set_rls_context
from .base import BaseAlertGenerator
from .context import AlertGeneratorContext
from .registry import register_alert_generator
from .result import AlertGeneratorResult
from .runner import AlertGeneratorRunner


@dataclass(slots=True)
class PecuariaAlertGenerationResult:
    lotes_sem_pesagem: int = 0
    vacinacoes_atrasadas: int = 0
    custos_sanitarios_altos: int = 0
    diagnosticos_pendentes: int = 0
    partos_previstos: int = 0
    desmamas_pendentes: int = 0

    @property
    def total_alertas(self) -> int:
        return (
            self.lotes_sem_pesagem
            + self.vacinacoes_atrasadas
            + self.custos_sanitarios_altos
            + self.diagnosticos_pendentes
            + self.partos_previstos
            + self.desmamas_pendentes
        )


@register_alert_generator
class PecuariaAlertGenerator(BaseAlertGenerator):
    """Generates canonical livestock alerts from existing pecuaria signals."""

    generator_name = "pecuaria"
    domain = Domain.LIVESTOCK
    category = Category.PRODUCAO
    event_types = (
        "pecuaria.vacinacao.registrada",
        "pecuaria.planejamento.sanitario.atualizado",
        "pecuaria.reproducao.registrada",
        "pecuaria.reproducao.diagnostico.pendente",
        "pecuaria.reproducao.parto.previsto",
        "pecuaria.reproducao.desmama.pendente",
    )
    ACTION_URL_LOTE = "/dashboard/pecuaria/lotes"
    ACTION_URL_MANEJO = "/dashboard/pecuaria/manejo"

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        """Execute the canonical Pecuaria generator contract."""

        await set_rls_context(self.session, context.tenant_id)
        dias_sem_pesagem = int(context.metadata.get("dias_sem_pesagem", 45))
        limite_custo = float(context.metadata.get("limite_custo_sanitario_por_cabeca", 50.0))
        counters = {
            "lotes_sem_pesagem": 0,
            "vacinacoes_atrasadas": 0,
            "custos_sanitarios_altos": 0,
            "diagnosticos_pendentes": 0,
            "partos_previstos": 0,
            "desmamas_pendentes": 0,
        }
        result = AlertGeneratorResult(
            generator_name=self.generator_name, metadata={"rule_counters": counters}
        )
        for lote in await self._lotes_ativos(context.tenant_id, context.unidade_produtiva_id):
            resumo = await self._resumo_lote(context.tenant_id, lote.id)
            if self._deve_alertar_pesagem(resumo, dias_sem_pesagem):
                created = await self._emitir_alerta_sem_pesagem(
                    context.tenant_id, lote, resumo, dias_sem_pesagem
                )
                result.created += created
                result.updated += 1 - created
                counters["lotes_sem_pesagem"] += 1
            if self._deve_alertar_custo(resumo, limite_custo):
                created = await self._emitir_alerta_custo_sanitario(
                    context.tenant_id,
                    lote,
                    resumo,
                    limite_custo,
                )
                result.created += created
                result.updated += 1 - created
                counters["custos_sanitarios_altos"] += 1
        for tarefa in await self._vacinacoes_atrasadas(
            context.tenant_id, context.unidade_produtiva_id
        ):
            created = await self._emitir_alerta_vacinacao_atrasada(context.tenant_id, tarefa)
            result.created += created
            result.updated += 1 - created
            counters["vacinacoes_atrasadas"] += 1
        for tarefa in await self._diagnosticos_pendentes(
            context.tenant_id, context.unidade_produtiva_id
        ):
            created = await self._emitir_alerta_diagnostico_pendente(context.tenant_id, tarefa)
            result.created += created
            result.updated += 1 - created
            counters["diagnosticos_pendentes"] += 1
        for tarefa in await self._partos_previstos(
            context.tenant_id, context.unidade_produtiva_id
        ):
            created = await self._emitir_alerta_parto_previsto(context.tenant_id, tarefa)
            result.created += created
            result.updated += 1 - created
            counters["partos_previstos"] += 1
        for tarefa in await self._desmamas_pendentes(
            context.tenant_id, context.unidade_produtiva_id
        ):
            created = await self._emitir_alerta_desmama_pendente(context.tenant_id, tarefa)
            result.created += created
            result.updated += 1 - created
            counters["desmamas_pendentes"] += 1
        result.metadata = {"rule_counters": counters}
        return result

    async def gerar_alertas_pecuaria(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
        dias_sem_pesagem: int = 45,
        limite_custo_sanitario_por_cabeca: float = 50.0,
    ) -> PecuariaAlertGenerationResult:
        """Compatibility wrapper that preserves the legacy return type."""

        context = self._legacy_context(
            unidade_produtiva_id=unidade_produtiva_id,
            dias_sem_pesagem=dias_sem_pesagem,
            limite_custo_sanitario_por_cabeca=limite_custo_sanitario_por_cabeca,
        )
        result = await AlertGeneratorRunner().execute(self, context)
        counters = result.metadata.get("rule_counters", {})
        return PecuariaAlertGenerationResult(
            lotes_sem_pesagem=int(counters.get("lotes_sem_pesagem", 0)),
            vacinacoes_atrasadas=int(counters.get("vacinacoes_atrasadas", 0)),
            custos_sanitarios_altos=int(counters.get("custos_sanitarios_altos", 0)),
        )

    async def _emitir_alerta_sem_pesagem(
        self,
        tenant_id: uuid.UUID,
        lote: LoteAnimal,
        resumo: LoteIndicadoresResponse,
        dias_sem_pesagem: int,
    ) -> int:
        ultima = (
            resumo.ultima_pesagem.isoformat() if resumo.ultima_pesagem else "sem pesagem registrada"
        )
        return await self._create_alert(
            tenant_id=tenant_id,
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

    async def _emitir_alerta_vacinacao_atrasada(
        self, tenant_id: uuid.UUID, tarefa: TarefaCampo
    ) -> int:
        return await self._create_alert(
            tenant_id=tenant_id,
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

    async def _emitir_alerta_diagnostico_pendente(
        self, tenant_id: uuid.UUID, tarefa: TarefaCampo
    ) -> int:
        return await self._create_alert(
            tenant_id=tenant_id,
            title="Diagnóstico de prenhez pendente",
            message=(
                f"O diagnóstico de prenhez '{tarefa.titulo or tarefa.type}' do lote "
                f"{tarefa.lote_id} está pendente desde {self._format_date(tarefa.data_programada)}."
            ),
            severity=Severity.WARNING,
            priority=Priority.HIGH,
            trigger_type=TriggerType.RULE,
            source_type="PECUARIA_REPRODUCAO_DIAGNOSTICO_PENDENTE",
            source_id=str(tarefa.id),
            dedupe_key=f"pecuaria:reproducao_diagnostico_pendente:{tarefa.id}",
            action_label="Ver tarefa",
            action_url=self.ACTION_URL_MANEJO,
            unidade_produtiva_id=tarefa.unidade_produtiva_id,
            context={
                "tarefa_campo_id": str(tarefa.id),
                "lote_id": str(tarefa.lote_id) if tarefa.lote_id else None,
                "data_programada": self._format_date(tarefa.data_programada),
                "status_execucao": tarefa.status_execucao,
            },
        )

    async def _emitir_alerta_parto_previsto(
        self, tenant_id: uuid.UUID, tarefa: TarefaCampo
    ) -> int:
        return await self._create_alert(
            tenant_id=tenant_id,
            title="Parto previsto",
            message=(
                f"O parto '{tarefa.titulo or tarefa.type}' do lote {tarefa.lote_id} "
                f"está previsto para {self._format_date(tarefa.data_programada)}."
            ),
            severity=Severity.INFO,
            priority=Priority.NORMAL,
            trigger_type=TriggerType.RULE,
            source_type="PECUARIA_REPRODUCAO_PARTO_PREVISTO",
            source_id=str(tarefa.id),
            dedupe_key=f"pecuaria:reproducao_parto_previsto:{tarefa.id}",
            action_label="Ver tarefa",
            action_url=self.ACTION_URL_MANEJO,
            unidade_produtiva_id=tarefa.unidade_produtiva_id,
            context={
                "tarefa_campo_id": str(tarefa.id),
                "lote_id": str(tarefa.lote_id) if tarefa.lote_id else None,
                "data_programada": self._format_date(tarefa.data_programada),
                "status_execucao": tarefa.status_execucao,
            },
        )

    async def _emitir_alerta_desmama_pendente(
        self, tenant_id: uuid.UUID, tarefa: TarefaCampo
    ) -> int:
        return await self._create_alert(
            tenant_id=tenant_id,
            title="Desmama pendente",
            message=(
                f"A desmama '{tarefa.titulo or tarefa.type}' do lote {tarefa.lote_id} "
                f"está pendente desde {self._format_date(tarefa.data_programada)}."
            ),
            severity=Severity.WARNING,
            priority=Priority.NORMAL,
            trigger_type=TriggerType.RULE,
            source_type="PECUARIA_REPRODUCAO_DESMAMA_PENDENTE",
            source_id=str(tarefa.id),
            dedupe_key=f"pecuaria:reproducao_desmama_pendente:{tarefa.id}",
            action_label="Ver tarefa",
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
        tenant_id: uuid.UUID,
        lote: LoteAnimal,
        resumo: LoteIndicadoresResponse,
        limite_custo_sanitario_por_cabeca: float,
    ) -> int:
        return await self._create_alert(
            tenant_id=tenant_id,
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
        tenant_id: uuid.UUID,
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
    ) -> int:
        service = AlertLifecycleService(self.session, tenant_id)
        was_update = await has_active_alert(self.session, tenant_id, dedupe_key)
        payload = OperationalAlertCreate(
            tenant_id=tenant_id,
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
        return 0 if was_update else 1

    async def _lotes_ativos(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[LoteAnimal]:
        stmt = select(LoteAnimal).where(LoteAnimal.tenant_id == tenant_id, LoteAnimal.ativo)
        if unidade_produtiva_id is not None:
            stmt = stmt.where(LoteAnimal.unidade_produtiva_id == unidade_produtiva_id)
        rows = await self.session.execute(stmt.order_by(LoteAnimal.identificacao.asc()))
        return list(rows.scalars().all())

    async def _resumo_lote(
        self, tenant_id: uuid.UUID, lote_id: uuid.UUID
    ) -> LoteIndicadoresResponse:
        return await LoteIndicadoresService(self.session, tenant_id).resumir(lote_id)

    async def _vacinacoes_atrasadas(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.type == "VACINACAO",
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada < date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        rows = await self.session.execute(
            stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc())
        )
        return list(rows.scalars().all())

    async def _diagnosticos_pendentes(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.type == "DIAGNOSTICO_PRENHEZ",
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada < date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        rows = await self.session.execute(
            stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc())
        )
        return list(rows.scalars().all())

    async def _partos_previstos(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.type == "PARTO",
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada <= date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        rows = await self.session.execute(
            stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc())
        )
        return list(rows.scalars().all())

    async def _desmamas_pendentes(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.type == "DESMAME",
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada < date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        rows = await self.session.execute(
            stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc())
        )
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

    @staticmethod
    def _format_date(value: date | None) -> str:
        return value.isoformat() if value else "sem data"

    def _legacy_context(
        self,
        *,
        unidade_produtiva_id: uuid.UUID | None,
        dias_sem_pesagem: int,
        limite_custo_sanitario_por_cabeca: float,
    ) -> AlertGeneratorContext:
        tenant_id = self.tenant_id
        if tenant_id is None:
            raise ValueError("tenant_id must be provided for legacy Pecuaria execution.")
        return AlertGeneratorContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            metadata={
                "dias_sem_pesagem": dias_sem_pesagem,
                "limite_custo_sanitario_por_cabeca": limite_custo_sanitario_por_cabeca,
            },
        )
