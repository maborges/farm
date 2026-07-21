"""Executor periódico das políticas ERP agendadas."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_maker
from core.models import Tenant
from integracoes.erp.policy_service import ALLOWED_SCHEDULES
from integracoes.erp.provider_registry import erp_provider_registry
from integracoes.models import (
    IntegrationFeature,
    IntegrationJob,
    IntegrationJobStatus,
    IntegrationJobTrigger,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)

SCHEDULE_INTERVALS = {
    "*/5 * * * *": timedelta(minutes=5),
    "*/15 * * * *": timedelta(minutes=15),
    "*/30 * * * *": timedelta(minutes=30),
    "0 * * * *": timedelta(hours=1),
    "0 */6 * * *": timedelta(hours=6),
    "0 */12 * * *": timedelta(hours=12),
    "0 0 * * *": timedelta(days=1),
}
_SCHEDULER_ADVISORY_LOCK = 7_184_202_607_18


@dataclass(frozen=True)
class ScheduledPolicyRuntime:
    """Dados já resolvidos para uma execução agendada."""

    policy: IntegrationSyncPolicy
    feature: IntegrationFeature
    config: TenantIntegracao
    provider: MarketplaceIntegracao
    last_run_at: datetime | None


def is_policy_due(expression: str | None, last_run_at: datetime | None, now: datetime) -> bool:
    """Determinar vencimento para o conjunto controlado de frequências."""
    if expression not in ALLOWED_SCHEDULES:
        return False
    if last_run_at is None:
        return True
    return now - last_run_at.replace(tzinfo=None) >= SCHEDULE_INTERVALS[expression]


def supports_scheduled_runtime(feature: IntegrationFeature) -> bool:
    """Executar somente flows que o adapter declara como agendáveis no runtime."""
    settings = feature.settings_payload if isinstance(feature.settings_payload, dict) else {}
    return "AGENDADO" in (settings.get("runtime_sync_modes") or [])


async def run_scheduled_erp_cycle() -> int:
    """Executar uma passagem tenant-safe pelas políticas ERP agendadas."""
    async with async_session_maker() as lock_session:
        if not await _acquire_scheduler_lock(lock_session):
            logger.debug("erp_scheduled_sync_cycle_skipped reason=lock_busy")
            return 0
        try:
            tenant_ids = await _list_active_tenant_ids()
            executed = 0
            for tenant_id in tenant_ids:
                executed += await _run_tenant_cycle(tenant_id)
            return executed
        finally:
            await _release_scheduler_lock(lock_session)


async def _acquire_scheduler_lock(session: AsyncSession) -> bool:
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return True
    return bool(
        await session.scalar(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": _SCHEDULER_ADVISORY_LOCK},
        )
    )


async def _release_scheduler_lock(session: AsyncSession) -> None:
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    await session.execute(
        text("SELECT pg_advisory_unlock(:lock_id)"),
        {"lock_id": _SCHEDULER_ADVISORY_LOCK},
    )


async def _list_active_tenant_ids() -> list[uuid.UUID]:
    async with async_session_maker() as session:
        stmt = select(Tenant.id).where(Tenant.ativo.is_(True))
        return list((await session.execute(stmt)).scalars())


async def _run_tenant_cycle(tenant_id: uuid.UUID) -> int:
    async with async_session_maker() as session:
        await _set_tenant_context(session, tenant_id)
        try:
            policies = await _list_scheduled_policies(session, tenant_id)
            executed = 0
            for scheduled_policy in policies:
                if not supports_scheduled_runtime(scheduled_policy.feature):
                    logger.warning(
                        "erp_scheduled_sync_unsupported tenant_id={} feature={}",
                        tenant_id,
                        scheduled_policy.feature.codigo,
                    )
                    continue
                if not is_policy_due(
                    scheduled_policy.policy.trigger_expression,
                    scheduled_policy.last_run_at,
                    datetime.utcnow(),
                ):
                    continue
                if await _execute_policy(session, tenant_id, scheduled_policy):
                    executed += 1
            return executed
        finally:
            await _clear_tenant_context(session)


async def _list_scheduled_policies(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[ScheduledPolicyRuntime]:
    last_run = (
        select(
            IntegrationJob.sync_policy_id.label("policy_id"),
            func.max(IntegrationJob.created_at).label("last_run_at"),
        )
        .where(IntegrationJob.tenant_id == tenant_id)
        .group_by(IntegrationJob.sync_policy_id)
        .subquery()
    )
    stmt = (
        select(
            IntegrationSyncPolicy,
            IntegrationFeature,
            TenantIntegracao,
            MarketplaceIntegracao,
            last_run.c.last_run_at,
        )
        .join(IntegrationFeature, IntegrationSyncPolicy.feature_id == IntegrationFeature.id)
        .join(TenantIntegracao, IntegrationSyncPolicy.config_id == TenantIntegracao.id)
        .join(MarketplaceIntegracao, IntegrationSyncPolicy.provider_id == MarketplaceIntegracao.id)
        .outerjoin(last_run, last_run.c.policy_id == IntegrationSyncPolicy.id)
        .where(
            IntegrationSyncPolicy.tenant_id == tenant_id,
            IntegrationSyncPolicy.mode == "AGENDADO",
            IntegrationSyncPolicy.ativa.is_(True),
            IntegrationSyncPolicy.deleted_at.is_(None),
            IntegrationFeature.habilitada.is_(True),
            IntegrationFeature.deleted_at.is_(None),
            TenantIntegracao.deleted_at.is_(None),
            MarketplaceIntegracao.ativa.is_(True),
        )
    )
    rows = (await session.execute(stmt)).all()
    return [ScheduledPolicyRuntime(*row) for row in rows]


async def _execute_policy(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    scheduled_policy: ScheduledPolicyRuntime,
) -> bool:
    runtime = erp_provider_registry.resolve(scheduled_policy.provider.slug, session)
    job = _create_job(tenant_id, scheduled_policy)
    session.add(job)
    await session.flush()
    try:
        result = await asyncio.wait_for(
            runtime.sync_feature(
                str(tenant_id),
                scheduled_policy.feature.codigo,
                scheduled=True,
            ),
            timeout=scheduled_policy.policy.timeout_seconds,
        )
        _mark_job_success(job, result)
        await session.commit()
        return True
    except Exception as exc:
        _mark_job_failure(job, exc)
        await session.commit()
        logger.exception(
            "erp_scheduled_sync_failed tenant_id={} provider={} feature={}",
            tenant_id,
            scheduled_policy.provider.slug,
            scheduled_policy.feature.codigo,
        )
        return False


def _create_job(
    tenant_id: uuid.UUID,
    scheduled_policy: ScheduledPolicyRuntime,
) -> IntegrationJob:
    now = datetime.utcnow()
    return IntegrationJob(
        tenant_id=tenant_id,
        config_id=scheduled_policy.config.id,
        feature_id=scheduled_policy.feature.id,
        sync_policy_id=scheduled_policy.policy.id,
        provider_id=scheduled_policy.provider.id,
        status=IntegrationJobStatus.RUNNING.value,
        trigger_type=IntegrationJobTrigger.SCHEDULED.value,
        started_at=now,
        request_payload={"feature_code": scheduled_policy.feature.codigo},
    )


def _mark_job_success(job: IntegrationJob, result: dict[str, object]) -> None:
    processed = int(result.get("processados") or 0)
    job.status = IntegrationJobStatus.SUCCESS.value
    job.finished_at = datetime.utcnow()
    job.processados = processed
    job.sucessos = processed
    job.erros = 0
    job.result_payload = result


def _mark_job_failure(job: IntegrationJob, exc: Exception) -> None:
    job.status = IntegrationJobStatus.FAILED.value
    job.finished_at = datetime.utcnow()
    job.erros = 1
    job.error_message = str(exc)


async def _set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Fixar o tenant na conexão do worker durante commits do legado Sankhya."""
    session.info["tenant_id"] = str(tenant_id)
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
        {"tenant_id": str(tenant_id)},
    )


async def _clear_tenant_context(session: AsyncSession) -> None:
    """Limpar o contexto antes de devolver a conexão ao pool."""
    try:
        await session.rollback()
        await session.execute(text("RESET app.current_tenant_id"))
        await session.commit()
        session.info.pop("tenant_id", None)
    except Exception:
        await session.invalidate()
        raise
