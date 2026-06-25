from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from campo.models import TarefaCampo


@dataclass(slots=True)
class CampoAlertGenerationResult:
    tarefas_atrasadas: int = 0
    tarefas_invalidas: int = 0
    sync_falhas: int = 0

    @property
    def total_alertas(self) -> int:
        return self.tarefas_atrasadas + self.tarefas_invalidas + self.sync_falhas


class CampoAlertGenerator:
    """Generates canonical field-origin alerts for Campo/Operational tasks."""

    ACTION_URL = "/dashboard/operacional/campo/tarefas"

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def gerar_alertas_campo(self, unidade_produtiva_id: uuid.UUID | None = None) -> CampoAlertGenerationResult:
        """Scan Campo tasks and materialize canonical operational alerts.

        Args:
            unidade_produtiva_id: Optional production unit scope.

        Returns:
            Generation counters by rule family.

        Raises:
            BusinessRuleError / TenantViolationError: Propagated from the Alert Engine service.
        """
        await self._set_rls_context()
        result = CampoAlertGenerationResult()
        for tarefa in await self._tarefas_atrasadas(unidade_produtiva_id):
            await self._emitir_alerta_atraso(tarefa)
            result.tarefas_atrasadas += 1
        for tarefa in await self._tarefas_invalidas(unidade_produtiva_id):
            await self._emitir_alerta_invalido(tarefa)
            result.tarefas_invalidas += 1
        for tarefa in await self._tarefas_sync_falha(unidade_produtiva_id):
            await self._emitir_alerta_sync_falha(tarefa)
            result.sync_falhas += 1
        return result

    async def _emitir_alerta_atraso(self, tarefa: TarefaCampo) -> None:
        await self._create_alert(
            tarefa=tarefa,
            title="Tarefa atrasada",
            message=self._build_atraso_message(tarefa),
            severity=Severity.WARNING,
            priority=Priority.HIGH,
            source_type="CAMPO_TAREFA_ATRASADA",
            dedupe_key=f"campo:tarefa_atrasada:{tarefa.id}",
            source_label=str(tarefa.id),
        )

    async def _emitir_alerta_invalido(self, tarefa: TarefaCampo) -> None:
        await self._create_alert(
            tarefa=tarefa,
            title="Tarefa inválida",
            message=self._build_invalida_message(tarefa),
            severity=Severity.CRITICAL,
            priority=Priority.HIGH,
            source_type="CAMPO_TAREFA_INVALIDA",
            dedupe_key=f"campo:tarefa_invalida:{tarefa.id}",
            source_label=str(tarefa.id),
        )

    async def _emitir_alerta_sync_falha(self, tarefa: TarefaCampo) -> None:
        await self._create_alert(
            tarefa=tarefa,
            title="Falha de sincronização",
            message=self._build_sync_falha_message(tarefa),
            severity=Severity.CRITICAL,
            priority=Priority.URGENT,
            source_type="CAMPO_SYNC_FALHA",
            dedupe_key=f"campo:sync_falha:{tarefa.id}",
            source_label=str(tarefa.id),
        )

    async def _create_alert(
        self,
        *,
        tarefa: TarefaCampo,
        title: str,
        message: str,
        severity: Severity,
        priority: Priority,
        source_type: str,
        dedupe_key: str,
        source_label: str,
    ) -> None:
        service = AlertLifecycleService(self.session, self.tenant_id)
        payload = OperationalAlertCreate(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=tarefa.unidade_produtiva_id,
            domain=Domain.FIELD,
            category=Category.OPERACIONAL,
            title=title,
            message=message,
            severity=severity,
            priority=priority,
            status=AlertStatus.OPEN,
            trigger_type=TriggerType.RULE,
            source_type=source_type,
            source_id=source_label,
            source_event_ids=[],
            source_indicator_ids=[],
            dedupe_key=dedupe_key,
            action_label="Ver tarefa",
            action_url=self.ACTION_URL,
            context={
                "tarefa_campo_id": str(tarefa.id),
                "status_execucao": tarefa.status_execucao,
                "type": tarefa.type,
                "module": tarefa.module,
            },
        )
        await service.create_or_update_alert(payload)

    async def _tarefas_atrasadas(self, unidade_produtiva_id: uuid.UUID | None) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == self.tenant_id,
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada < date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        result = await self.session.execute(stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc()))
        return list(result.scalars().all())

    async def _tarefas_invalidas(self, unidade_produtiva_id: uuid.UUID | None) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == self.tenant_id,
            TarefaCampo.status_execucao == "INVALIDADA",
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        result = await self.session.execute(stmt.order_by(TarefaCampo.updated_at.asc()))
        return list(result.scalars().all())

    async def _tarefas_sync_falha(self, unidade_produtiva_id: uuid.UUID | None) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == self.tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.status_execucao == "CONCLUIDA",
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        result = await self.session.execute(stmt.order_by(TarefaCampo.updated_at.asc()))
        tarefas = list(result.scalars().all())
        return [tarefa for tarefa in tarefas if self._is_sync_failure(tarefa)]

    @staticmethod
    def _is_sync_failure(tarefa: TarefaCampo) -> bool:
        sync_meta = (tarefa.dados or {}).get("sync_pecuaria") or {}
        if sync_meta.get("status") != "ERROR":
            return False
        erros = sync_meta.get("erros") or []
        return bool(erros)

    @staticmethod
    def _build_atraso_message(tarefa: TarefaCampo) -> str:
        data_programada = tarefa.data_programada.isoformat() if tarefa.data_programada else "sem data"
        titulo = tarefa.titulo or tarefa.type
        return f"A tarefa '{titulo}' está programada para {data_programada} e continua em aberto."

    @staticmethod
    def _build_invalida_message(tarefa: TarefaCampo) -> str:
        motivo = (tarefa.motivo_invalidacao or "").strip() or "Motivo não informado."
        titulo = tarefa.titulo or tarefa.type
        return f"A tarefa '{titulo}' foi invalidada. Motivo: {motivo}"

    @staticmethod
    def _build_sync_falha_message(tarefa: TarefaCampo) -> str:
        sync_meta = (tarefa.dados or {}).get("sync_pecuaria") or {}
        erros = sync_meta.get("erros") or []
        detalhe = erros[0] if erros else "Falha sem detalhes registrados."
        titulo = tarefa.titulo or tarefa.type
        return f"A tarefa '{titulo}' apresentou falha no processamento de sincronização: {detalhe}"

    async def _set_rls_context(self) -> None:
        await self.session.execute(text(f"SET LOCAL app.current_tenant_id = '{self.tenant_id}';"))

