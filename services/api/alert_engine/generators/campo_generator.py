from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from campo.models import TarefaCampo

from ._support import has_active_alert, set_rls_context
from .base import BaseAlertGenerator
from .context import AlertGeneratorContext
from .registry import register_alert_generator
from .result import AlertGeneratorResult
from .runner import AlertGeneratorRunner


@dataclass(slots=True)
class CampoAlertGenerationResult:
    tarefas_atrasadas: int = 0
    tarefas_invalidas: int = 0
    sync_falhas: int = 0

    @property
    def total_alertas(self) -> int:
        return self.tarefas_atrasadas + self.tarefas_invalidas + self.sync_falhas


@register_alert_generator
class CampoAlertGenerator(BaseAlertGenerator):
    """Generates canonical field-origin alerts for Campo/Operational tasks."""

    generator_name = "campo"
    domain = Domain.FIELD
    category = Category.OPERACIONAL
    event_types = (
        "campo.tarefa.invalidada",
        "campo.sync.falha",
    )
    ACTION_URL = "/dashboard/operacional/campo/tarefas"

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        """Execute the canonical Campo generator contract.

        Cada tarefa é processada dentro de um SAVEPOINT (`begin_nested`) —
        não um `session.rollback()` da transação inteira. Confirmado ao vivo
        em produção (2026-08-14) que `session.rollback()` após uma falha de
        flush NÃO deixa a sessão de fato reutilizável nesse stack (SQLAlchemy
        async + asyncpg): o próximo `db.commit()` do chamador ainda falhava
        com PendingRollbackError, mesmo com o rollback "bem-sucedido" e sem
        exceção visível. SAVEPOINT resolve porque só desfaz o item que
        falhou, sem invalidar a transação externa. Ver memória do projeto
        project_tres_sistemas_alertas_mapeados.
        """
        from loguru import logger

        await set_rls_context(self.session, context.tenant_id)
        counters = {"tarefas_atrasadas": 0, "tarefas_invalidas": 0, "sync_falhas": 0}
        result = AlertGeneratorResult(
            generator_name=self.generator_name, metadata={"rule_counters": counters}
        )

        async def _processar(tarefas, emitir, contador_key):
            for tarefa in tarefas:
                try:
                    async with self.session.begin_nested():
                        created = await emitir(context.tenant_id, tarefa)
                    result.created += created
                    result.updated += 1 - created
                    counters[contador_key] += 1
                except Exception as exc:  # pragma: no cover - defensive isolation
                    logger.bind(
                        component="campo_alert_generator",
                        tenant_id=str(context.tenant_id),
                        tarefa_id=str(tarefa.id),
                        contador=contador_key,
                    ).exception("campo_alert_generator_item_failed")
                    result.errors += 1

        await _processar(
            await self._tarefas_atrasadas(context.tenant_id, context.unidade_produtiva_id),
            self._emitir_alerta_atraso,
            "tarefas_atrasadas",
        )
        await _processar(
            await self._tarefas_invalidas(context.tenant_id, context.unidade_produtiva_id),
            self._emitir_alerta_invalido,
            "tarefas_invalidas",
        )
        await _processar(
            await self._tarefas_sync_falha(context.tenant_id, context.unidade_produtiva_id),
            self._emitir_alerta_sync_falha,
            "sync_falhas",
        )
        result.metadata = {"rule_counters": counters}
        return result

    async def gerar_alertas_campo(
        self, unidade_produtiva_id: uuid.UUID | None = None
    ) -> CampoAlertGenerationResult:
        """Compatibility wrapper that preserves the legacy return type."""

        context = self._legacy_context(unidade_produtiva_id)
        result = await AlertGeneratorRunner().execute(self, context)
        counters = result.metadata.get("rule_counters", {})
        return CampoAlertGenerationResult(
            tarefas_atrasadas=int(counters.get("tarefas_atrasadas", 0)),
            tarefas_invalidas=int(counters.get("tarefas_invalidas", 0)),
            sync_falhas=int(counters.get("sync_falhas", 0)),
        )

    async def _emitir_alerta_atraso(self, tenant_id: uuid.UUID, tarefa: TarefaCampo) -> int:
        return await self._create_alert(
            tenant_id=tenant_id,
            tarefa=tarefa,
            title="Tarefa atrasada",
            message=self._build_atraso_message(tarefa),
            severity=Severity.WARNING,
            priority=Priority.HIGH,
            source_type="CAMPO_TAREFA_ATRASADA",
            dedupe_key=f"campo:tarefa_atrasada:{tarefa.id}",
            source_label=str(tarefa.id),
        )

    async def _emitir_alerta_invalido(self, tenant_id: uuid.UUID, tarefa: TarefaCampo) -> int:
        return await self._create_alert(
            tenant_id=tenant_id,
            tarefa=tarefa,
            title="Tarefa inválida",
            message=self._build_invalida_message(tarefa),
            severity=Severity.CRITICAL,
            priority=Priority.HIGH,
            source_type="CAMPO_TAREFA_INVALIDA",
            dedupe_key=f"campo:tarefa_invalida:{tarefa.id}",
            source_label=str(tarefa.id),
        )

    async def _emitir_alerta_sync_falha(self, tenant_id: uuid.UUID, tarefa: TarefaCampo) -> int:
        return await self._create_alert(
            tenant_id=tenant_id,
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
        tenant_id: uuid.UUID,
        tarefa: TarefaCampo,
        title: str,
        message: str,
        severity: Severity,
        priority: Priority,
        source_type: str,
        dedupe_key: str,
        source_label: str,
    ) -> int:
        service = AlertLifecycleService(self.session, tenant_id)
        was_update = await has_active_alert(self.session, tenant_id, dedupe_key)
        payload = OperationalAlertCreate(
            tenant_id=tenant_id,
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
        return 0 if was_update else 1

    async def _tarefas_atrasadas(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada < date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        result = await self.session.execute(
            stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc())
        )
        return list(result.scalars().all())

    async def _tarefas_invalidas(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.status_execucao == "INVALIDADA",
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        result = await self.session.execute(stmt.order_by(TarefaCampo.updated_at.asc()))
        return list(result.scalars().all())

    async def _tarefas_sync_falha(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
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
        data_programada = (
            tarefa.data_programada.isoformat() if tarefa.data_programada else "sem data"
        )
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

    def _legacy_context(self, unidade_produtiva_id: uuid.UUID | None) -> AlertGeneratorContext:
        tenant_id = self.tenant_id
        if tenant_id is None:
            raise ValueError("tenant_id must be provided for legacy Campo execution.")
        return AlertGeneratorContext(tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id)
