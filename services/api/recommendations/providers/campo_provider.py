from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from campo.models import DispositivoCampo, SyncTombstone, TarefaCampo

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal
from ._common import build_candidate_context, build_route_target, stable_dedupe_key, tenant_signal_ids


class CampoRecommendationProvider(RecommendationProvider):
    provider_name = "campo"
    domains = ("FIELD",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None:
            return []

        signal_ids = tenant_signal_ids(signals, context.tenant_id)
        payload = context.payload or {}
        dias_sem_sync = int(payload.get("dias_sem_sync", 2))

        dispositivos = await self._listar_dispositivos(context.tenant_id, context.unidade_produtiva_id)
        tarefas = await self._listar_tarefas(context.tenant_id, context.unidade_produtiva_id)
        sync_falhas = await self._listar_sync_falhas(context.tenant_id, context.unidade_produtiva_id)
        tombstones = await self._listar_tombstones(context.tenant_id, context.unidade_produtiva_id)

        candidates: list[RecommendationCandidate] = []
        for device in dispositivos:
            if self._sync_desatualizado(device.last_sync_at, dias_sem_sync):
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="DISPOSITIVO",
                        scope_id=str(device.id),
                        rule_code="CAMPO_SYNC_DESATUALIZADO",
                        title="Sincronização do dispositivo desatualizada",
                        summary="O dispositivo de campo está há muito tempo sem sincronização.",
                        rationale="A ausência de sync recente reduz a confiança dos dados coletados em campo.",
                        priority=RecommendationPriority.HIGH,
                        confidence=Decimal("0.94"),
                        action_label="Sincronizar dispositivo",
                        action_target=build_route_target("/dashboard/operacional/campo/tarefas", device.id),
                        source_type=RecommendationSourceType.INDICATOR,
                        source_signal_ids=signal_ids,
                        context_data={
                            "dispositivo_id": str(device.id),
                            "nome": device.nome,
                            "last_sync_at": device.last_sync_at.isoformat() if device.last_sync_at else None,
                            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
                            "dias_sem_sync": dias_sem_sync,
                        },
                    )
                )

        for tarefa in tarefas:
            candidates.append(
                self._candidate(
                    context,
                    scope_type="TAREFA",
                    scope_id=str(tarefa.id),
                    rule_code="CAMPO_TAREFA_ATRASADA",
                    title="Tarefa de campo atrasada",
                    summary=f"A tarefa {tarefa.titulo or tarefa.type} está atrasada.",
                    rationale="Tarefas atrasadas afetam a cadência operacional e a atualização dos dados de campo.",
                    priority=RecommendationPriority.HIGH,
                    confidence=Decimal("0.90"),
                    action_label="Abrir tarefa",
                    action_target=build_route_target("/dashboard/operacional/campo/tarefas", tarefa.id),
                    source_type=RecommendationSourceType.EVENT,
                    source_signal_ids=signal_ids,
                    context_data={
                        "tarefa_id": str(tarefa.id),
                        "status_execucao": tarefa.status_execucao,
                        "data_programada": tarefa.data_programada.isoformat() if tarefa.data_programada else None,
                        "module": tarefa.module,
                        "type": tarefa.type,
                    },
                )
            )

        for tarefa in sync_falhas:
            candidates.append(
                self._candidate(
                    context,
                    scope_type="TAREFA",
                    scope_id=str(tarefa.id),
                    rule_code="CAMPO_SYNC_FALHA_PECUARIA",
                    title="Falha de sincronização de tarefa",
                    summary="Uma tarefa concluída da pecuária apresenta falha no processamento de sync.",
                    rationale="Falhas de sincronização precisam ser tratadas para evitar divergência entre campo e backend.",
                    priority=RecommendationPriority.URGENT,
                    confidence=Decimal("0.97"),
                    action_label="Reprocessar sync",
                    action_target=build_route_target("/dashboard/operacional/campo/tarefas", tarefa.id),
                    source_type=RecommendationSourceType.EVENT,
                    source_signal_ids=signal_ids,
                    context_data={
                        "tarefa_id": str(tarefa.id),
                        "status_execucao": tarefa.status_execucao,
                        "sync_status": (tarefa.dados or {}).get("sync_pecuaria", {}).get("status"),
                    },
                )
            )

        if tombstones:
            latest_tombstone = max(tombstones, key=lambda item: item.deleted_at)
            candidates.append(
                self._candidate(
                    context,
                    scope_type="SYNC",
                    scope_id=str(latest_tombstone.id),
                    rule_code="CAMPO_TOMBSTONE_PENDENTE",
                    title="Tombstones aguardando sincronização",
                    summary="Há deleções de campo a considerar no próximo sync.",
                    rationale="Tombstones recentes indicam que o próximo pull precisa atualizar o dispositivo com as remoções.",
                    priority=RecommendationPriority.NORMAL,
                    confidence=Decimal("0.78"),
                    action_label="Sincronizar",
                    action_target=build_route_target("/dashboard/operacional/campo/tarefas", latest_tombstone.id),
                    source_type=RecommendationSourceType.SYSTEM,
                    source_signal_ids=signal_ids,
                    context_data={
                        "tombstone_id": str(latest_tombstone.id),
                        "entity_type": latest_tombstone.entity_type,
                        "deleted_at": latest_tombstone.deleted_at.isoformat(),
                        "total_tombstones": len(tombstones),
                    },
                )
            )

        return candidates

    async def _listar_dispositivos(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[DispositivoCampo]:
        stmt = select(DispositivoCampo).where(
            DispositivoCampo.tenant_id == tenant_id,
            DispositivoCampo.status == "ATIVO",
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(DispositivoCampo.fazenda_ids.contains([unidade_produtiva_id]))
        stmt = stmt.order_by(DispositivoCampo.last_sync_at.asc().nullsfirst(), DispositivoCampo.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_tarefas(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada < date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        stmt = stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_sync_falhas(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.status_execucao == "CONCLUIDA",
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        tarefas = list((await self.session.execute(stmt.order_by(TarefaCampo.updated_at.asc()))).scalars().all())
        return [tarefa for tarefa in tarefas if self._is_sync_failure(tarefa)]

    async def _listar_tombstones(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[SyncTombstone]:
        stmt = select(SyncTombstone).where(SyncTombstone.tenant_id == tenant_id)
        if unidade_produtiva_id is not None:
            # Tombstones não carregam unidade; usamos apenas o tenant e o contexto da execução.
            pass
        stmt = stmt.order_by(SyncTombstone.deleted_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    @staticmethod
    def _is_sync_failure(tarefa: TarefaCampo) -> bool:
        sync_meta = (tarefa.dados or {}).get("sync_pecuaria") or {}
        if sync_meta.get("status") != "ERROR":
            return False
        return bool(sync_meta.get("erros") or [])

    @staticmethod
    def _sync_desatualizado(last_sync_at: datetime | None, dias_sem_sync: int) -> bool:
        if last_sync_at is None:
            return True
        atual = datetime.now(timezone.utc)
        if last_sync_at.tzinfo is None:
            last_sync_at = last_sync_at.replace(tzinfo=timezone.utc)
        return (atual - last_sync_at).days >= dias_sem_sync

    def _candidate(
        self,
        context: OperationalContext,
        *,
        scope_type: str,
        scope_id: str,
        rule_code: str,
        title: str,
        summary: str,
        rationale: str,
        priority: RecommendationPriority,
        confidence: Decimal,
        action_label: str,
        action_target: str,
        source_type: RecommendationSourceType,
        source_signal_ids: list[UUID],
        context_data: dict[str, object],
    ) -> RecommendationCandidate:
        return RecommendationCandidate(
            tenant_id=context.tenant_id,
            unidade_produtiva_id=context.unidade_produtiva_id,
            domain=RecommendationDomain.FIELD,
            priority=priority,
            source_type=source_type,
            action_type=RecommendationActionType.OPEN_ROUTE,
            provider_name=self.provider_name,
            rule_code=rule_code,
            scope_type=scope_type,
            scope_id=scope_id,
            title=title,
            summary=summary,
            rationale=rationale,
            dedupe_key=stable_dedupe_key(
                self.provider_name,
                context.tenant_id,
                scope_id,
                rule_code,
                context.unidade_produtiva_id,
            ),
            source_signal_ids=source_signal_ids,
            confidence=confidence,
            action_label=action_label,
            action_target=action_target,
            context=build_candidate_context(context, context_data),
        )
