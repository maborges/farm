from __future__ import annotations

from datetime import datetime, timezone
from itertools import islice
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_maker
from core.models.tenant import Tenant

from .engine import RecommendationEngineResult
from .enums import RecommendationDomain
from .lifecycle_service import RecommendationLifecycleService
from .provider import RecommendationProvider
from .registry import RecommendationProviderRegistry, recommendation_provider_registry
from .runner import RecommendationExecutionRunner
from .schemas import RecommendationEngineRunResultResponse, RecommendationSignal


class RecommendationSchedulerExecution(BaseModel):
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: RecommendationDomain
    provider_name: str
    status: str
    candidate_count: int = 0
    created: int = 0
    updated: int = 0
    expired: int = 0
    errors: int = 0
    duration_ms: int = 0
    batch_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RecommendationSchedulerResult(BaseModel):
    scheduler_run_id: UUID
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: RecommendationDomain | None = None
    dry_run: bool = False
    batch_size: int = 1
    total_batches: int = 0
    providers_requested: int = 0
    providers_executed: int = 0
    candidates_total: int = 0
    recommendations_created: int = 0
    recommendations_updated: int = 0
    recommendations_expired: int = 0
    errors: int = 0
    duration_ms: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    provider_names: list[str] = Field(default_factory=list)
    executions: list[RecommendationSchedulerExecution] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RecommendationSchedulerService:
    """Controlled orchestration for global recommendation runs."""

    def __init__(
        self,
        session: AsyncSession,
        registry: RecommendationProviderRegistry | None = None,
        runner: RecommendationExecutionRunner | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or recommendation_provider_registry
        self.runner = runner or RecommendationExecutionRunner(session, registry=self.registry)

    async def run_scheduled_recommendations(
        self,
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None = None,
        domain: RecommendationDomain | None = None,
        dry_run: bool = False,
        batch_size: int = 10,
        max_batches: int | None = None,
        signals: list[RecommendationSignal] | None = None,
    ) -> RecommendationSchedulerResult:
        started_at = datetime.now(timezone.utc)
        start = perf_counter()
        scheduler_run_id = uuid4()
        provider_classes = await self._resolve_provider_classes(domain)
        result = RecommendationSchedulerResult(
            scheduler_run_id=scheduler_run_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=domain,
            dry_run=dry_run,
            batch_size=max(1, batch_size),
            total_batches=0,
            providers_requested=len(provider_classes),
            started_at=started_at,
        )
        bound_logger = logger.bind(
            component="recommendation_scheduler_service",
            scheduler_run_id=str(scheduler_run_id),
            tenant_id=str(tenant_id),
            unidade_produtiva_id=str(unidade_produtiva_id) if unidade_produtiva_id else None,
            domain=domain.value if domain else None,
            dry_run=dry_run,
            batch_size=batch_size,
            max_batches=max_batches,
        )
        bound_logger.info("recommendation_scheduler_started")
        if not provider_classes:
            result.warnings.append("no_providers_registered")
            result.duration_ms = int((perf_counter() - start) * 1000)
            result.finished_at = datetime.now(timezone.utc)
            bound_logger.info("recommendation_scheduler_finished")
            return result

        executed_batches = 0
        for batch_index, provider_batch in enumerate(self._chunked(provider_classes, batch_size), start=1):
            if max_batches is not None and executed_batches >= max_batches:
                result.warnings.append("batch_limit_reached")
                break
            executed_batches += 1
            result.total_batches += 1
            for provider_cls in provider_batch:
                provider_name = getattr(provider_cls, "provider_name", provider_cls.__name__)
                provider_domain = self._provider_domain(provider_cls, domain)
                execution_start = perf_counter()
                try:
                    engine_result = await self.runner.run_provider(
                        tenant_id=tenant_id,
                        provider_cls=provider_cls,
                        signals=signals,
                        unidade_produtiva_id=unidade_produtiva_id,
                        domain=provider_domain,
                        dry_run=dry_run,
                        metadata={
                            "scheduler_run_id": str(scheduler_run_id),
                            "batch_index": batch_index,
                            "provider_name": provider_name,
                            "requested_domain": domain.value if domain else None,
                            "dry_run": dry_run,
                        },
                    )
                except Exception as exc:  # pragma: no cover - defensive isolation
                    execution = self._failed_execution(
                        tenant_id=tenant_id,
                        unidade_produtiva_id=unidade_produtiva_id,
                        provider_name=provider_name,
                        domain=provider_domain,
                        batch_index=batch_index,
                        started_at=datetime.now(timezone.utc),
                        exc=exc,
                    )
                    self._accumulate(result, execution)
                    bound_logger.bind(
                        provider_name=provider_name,
                        domain=provider_domain.value,
                        batch_index=batch_index,
                        status=execution.status,
                        errors=execution.errors,
                    ).exception("recommendation_scheduler_provider_failed")
                    continue

                execution = self._to_execution(
                    tenant_id=tenant_id,
                    unidade_produtiva_id=unidade_produtiva_id,
                    domain=provider_domain,
                    batch_index=batch_index,
                    result=engine_result,
                    duration_ms=int((perf_counter() - execution_start) * 1000),
                )
                self._accumulate(result, execution)
                bound_logger.bind(
                    provider_name=provider_name,
                    domain=provider_domain.value,
                    batch_index=batch_index,
                    status=execution.status,
                    candidates=execution.candidate_count,
                    recommendations_generated=execution.created,
                    recommendations_updated=execution.updated,
                    recommendations_expired=execution.expired,
                    failures=execution.errors,
                    duration_ms=execution.duration_ms,
                    dry_run=dry_run,
                ).info("recommendation_scheduler_provider_finished")

        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(timezone.utc)
        bound_logger.bind(
            providers_requested=result.providers_requested,
            providers_executed=result.providers_executed,
            candidates_total=result.candidates_total,
            recommendations_created=result.recommendations_created,
            recommendations_updated=result.recommendations_updated,
            recommendations_expired=result.recommendations_expired,
            errors=result.errors,
            total_batches=result.total_batches,
            duration_ms=result.duration_ms,
        ).info("recommendation_scheduler_finished")
        return result

    async def _resolve_provider_classes(
        self,
        domain: RecommendationDomain | None,
    ) -> tuple[type[RecommendationProvider], ...]:
        if domain is None:
            return self.registry.list_providers()
        return self.registry.find_by_domain(domain.value)

    @staticmethod
    def _provider_domain(
        provider_cls: type[RecommendationProvider],
        requested_domain: RecommendationDomain | None,
    ) -> RecommendationDomain:
        if requested_domain is not None:
            return requested_domain
        for value in getattr(provider_cls, "domains", ()):
            try:
                return RecommendationDomain(str(value).upper())
            except ValueError:
                continue
        return RecommendationDomain.SYSTEM

    @staticmethod
    def _chunked(
        values: tuple[type[RecommendationProvider], ...],
        batch_size: int,
    ) -> tuple[tuple[type[RecommendationProvider], ...], ...]:
        if batch_size <= 0:
            batch_size = 1
        iterator = iter(values)
        batches: list[tuple[type[RecommendationProvider], ...]] = []
        while True:
            batch = tuple(islice(iterator, batch_size))
            if not batch:
                break
            batches.append(batch)
        return tuple(batches)

    @staticmethod
    def _to_execution(
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        domain: RecommendationDomain,
        batch_index: int,
        result: RecommendationEngineResult,
        duration_ms: int,
    ) -> RecommendationSchedulerExecution:
        engine_execution = result.executions[0] if result.executions else None
        candidate_count = (
            engine_execution.candidate_count
            if engine_execution is not None
            else result.candidates_total
        )
        created = engine_execution.created if engine_execution is not None else result.recommendations_created
        updated = engine_execution.updated if engine_execution is not None else result.recommendations_updated
        errors = engine_execution.errors if engine_execution is not None else result.errors
        status = engine_execution.status if engine_execution is not None else "success"
        return RecommendationSchedulerExecution(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=domain,
            provider_name=(
                engine_execution.provider_name
                if engine_execution is not None
                else result.executions[0].provider_name
                if result.executions
                else "unknown"
            ),
            status=status,
            candidate_count=candidate_count,
            created=created,
            updated=updated,
            errors=errors,
            duration_ms=duration_ms,
            batch_index=batch_index,
            metadata={
                "dry_run": result.dry_run,
                "run_id": str(result.run_id),
                "engine_duration_ms": result.duration_ms,
            },
        )

    @staticmethod
    def _failed_execution(
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        provider_name: str,
        domain: RecommendationDomain,
        batch_index: int,
        started_at: datetime,
        exc: Exception,
    ) -> RecommendationSchedulerExecution:
        finished_at = datetime.now(timezone.utc)
        return RecommendationSchedulerExecution(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=domain,
            provider_name=provider_name,
            status="failed",
            errors=1,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            batch_index=batch_index,
            metadata={
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            },
        )

    @staticmethod
    def _accumulate(
        result: RecommendationSchedulerResult,
        execution: RecommendationSchedulerExecution,
    ) -> None:
        result.providers_executed += 1
        result.candidates_total += execution.candidate_count
        result.recommendations_created += execution.created
        result.recommendations_updated += execution.updated
        result.recommendations_expired += execution.expired
        result.errors += execution.errors
        result.provider_names.append(execution.provider_name)
        result.executions.append(execution)


async def run_scheduled_recommendations(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    domain: RecommendationDomain | None = None,
    dry_run: bool = False,
    batch_size: int = 10,
    max_batches: int | None = None,
    signals: list[RecommendationSignal] | None = None,
) -> RecommendationEngineRunResultResponse:
    """Convenience helper for controlled operational runs."""

    result = await RecommendationSchedulerService(session).run_scheduled_recommendations(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        domain=domain,
        dry_run=dry_run,
        batch_size=batch_size,
        max_batches=max_batches,
        signals=signals,
    )
    return RecommendationEngineRunResultResponse.model_validate(result.model_dump())


_SCHEDULER_ADVISORY_LOCK = 7_184_202_607_29


async def run_scheduled_recommendation_cycle(
    *,
    dry_run: bool = False,
    batch_size: int = 10,
    max_batches: int | None = None,
) -> int:
    """Run the existing recommendation scheduler once for each active tenant."""
    async with async_session_maker() as lock_session:
        if not await _acquire_scheduler_lock(lock_session):
            logger.bind(component="recommendation_scheduler_cycle").debug(
                "recommendation_scheduler_cycle_skipped",
                reason="lock_busy",
            )
            return 0
        try:
            tenant_ids = await _list_active_tenant_ids()
            completed = 0
            for tenant_id in tenant_ids:
                result = await _run_tenant_cycle(
                    tenant_id,
                    dry_run=dry_run,
                    batch_size=batch_size,
                    max_batches=max_batches,
                )
                if result is not None:
                    completed += 1
            return completed
        finally:
            await _release_scheduler_lock(lock_session)


async def _run_tenant_cycle(
    tenant_id: UUID,
    *,
    dry_run: bool,
    batch_size: int,
    max_batches: int | None,
) -> RecommendationSchedulerResult | None:
    """Run providers in one isolated RLS session and commit their aggregate result."""
    async with async_session_maker() as session:
        await _set_tenant_context(session, tenant_id)
        started_at = perf_counter()
        try:
            lifecycle = RecommendationLifecycleService(session, tenant_id)
            expired = 0 if dry_run else await lifecycle.expire_due_recommendations()
            result = await RecommendationSchedulerService(session).run_scheduled_recommendations(
                tenant_id=tenant_id,
                dry_run=dry_run,
                batch_size=batch_size,
                max_batches=max_batches,
            )
            result.recommendations_expired = expired
            if not dry_run:
                await session.commit()
            logger.bind(
                component="recommendation_scheduler_cycle",
                tenant_id=str(tenant_id),
                provider="all",
                duration_ms=int((perf_counter() - started_at) * 1000),
                recommendations_generated=result.recommendations_created,
                recommendations_updated=result.recommendations_updated,
                recommendations_expired=expired,
                failures=result.errors,
                dry_run=dry_run,
            ).info("recommendation_scheduler_tenant_finished")
            return result
        except Exception as exc:
            await session.rollback()
            logger.bind(
                component="recommendation_scheduler_cycle",
                tenant_id=str(tenant_id),
                provider="all",
                duration_ms=int((perf_counter() - started_at) * 1000),
                recommendations_generated=0,
                recommendations_updated=0,
                recommendations_expired=0,
                failures=1,
                dry_run=dry_run,
                exception_type=exc.__class__.__name__,
            ).exception("recommendation_scheduler_tenant_failed")
            return None
        finally:
            await _clear_tenant_context(session)


async def _acquire_scheduler_lock(session: AsyncSession) -> bool:
    """Acquire the PostgreSQL advisory lock used to prevent overlapping cycles."""
    if session.get_bind().dialect.name != "postgresql":
        return True
    return bool(
        await session.scalar(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": _SCHEDULER_ADVISORY_LOCK},
        )
    )


async def _release_scheduler_lock(session: AsyncSession) -> None:
    """Release the cycle lock before returning its connection to the pool."""
    if session.get_bind().dialect.name == "postgresql":
        try:
            await session.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": _SCHEDULER_ADVISORY_LOCK},
            )
        except DBAPIError as exc:
            # PostgreSQL releases session advisory locks when the connection
            # closes. A connection lost during a long tenant cycle therefore
            # has no lock left to release; invalidating it avoids returning a
            # broken connection to the pool without turning cleanup into a
            # false scheduler-cycle failure.
            if "connection is closed" not in str(exc.orig).lower():
                raise
            logger.bind(component="recommendation_scheduler_cycle").warning(
                "recommendation_scheduler_lock_released_by_connection_close"
            )
            await session.invalidate()


async def _list_active_tenant_ids() -> list[UUID]:
    """List scheduler targets without sharing tenant sessions between iterations."""
    async with async_session_maker() as session:
        rows = await session.execute(select(Tenant.id).where(Tenant.ativo.is_(True)))
        return list(rows.scalars())


async def _set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """Set the RLS tenant context for the whole worker session."""
    session.info["tenant_id"] = str(tenant_id)
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
        {"tenant_id": str(tenant_id)},
    )


async def _clear_tenant_context(session: AsyncSession) -> None:
    """Reset RLS state before the pooled connection can be reused."""
    try:
        await session.rollback()
        await session.execute(text("RESET app.current_tenant_id"))
        await session.commit()
        session.info.pop("tenant_id", None)
    except Exception:
        await session.invalidate()
        raise
