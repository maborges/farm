from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.generators import (
    AlertGeneratorContext,
    AlertGeneratorRegistry,
    AlertGeneratorResult,
    AlertGeneratorRunner,
    alert_generator_registry,
)
from alert_engine.generators.base import BaseAlertGenerator
from alert_engine.models import Domain
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva


class AlertSchedulerExecution(BaseModel):
    """Canonical per-generator execution summary for scheduled runs."""

    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: Domain
    generator_name: str
    status: str
    created: int = 0
    updated: int = 0
    ignored: int = 0
    skipped: int = 0
    warnings: int = 0
    errors: int = 0
    duration_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AlertSchedulerResult(BaseModel):
    """Canonical aggregate result for scheduled Alert Engine execution."""

    scheduler_run_id: UUID
    generators_executed: int = 0
    alerts_created: int = 0
    alerts_updated: int = 0
    alerts_ignored: int = 0
    alerts_skipped: int = 0
    warnings: int = 0
    errors: int = 0
    duration_ms: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    executions: list[AlertSchedulerExecution] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AlertSchedulerService:
    """Internal scheduler for canonical Alert Engine generators."""

    def __init__(
        self,
        session: AsyncSession,
        registry: AlertGeneratorRegistry | None = None,
        runner: AlertGeneratorRunner | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or alert_generator_registry
        self.runner = runner or AlertGeneratorRunner()

    async def run_scheduled_alerts(
        self,
        tenant_id: UUID | None = None,
        unidade_produtiva_id: UUID | None = None,
        domains: list[str] | None = None,
        dry_run: bool = False,
    ) -> AlertSchedulerResult:
        """Execute scheduled generators for the selected targets.

        Args:
            tenant_id: Optional tenant scope.
            unidade_produtiva_id: Optional production-unit scope.
            domains: Optional domain filter.
            dry_run: If True, roll back each generator execution.

        Returns:
            Aggregated scheduler result with per-generator executions.
        """

        started_at = datetime.now(timezone.utc)  # noqa: UP017
        start = perf_counter()
        scheduler_run_id = uuid4()
        targets = await self._resolve_targets(tenant_id, unidade_produtiva_id)
        domain_filter = self._normalize_domains(domains)
        result = AlertSchedulerResult(
            scheduler_run_id=scheduler_run_id,
            started_at=started_at,
        )
        bound_logger = logger.bind(
            component="alert_scheduler_service",
            scheduler_run_id=str(scheduler_run_id),
            tenant_id=str(tenant_id) if tenant_id else None,
            unidade_produtiva_id=str(unidade_produtiva_id) if unidade_produtiva_id else None,
            dry_run=dry_run,
        )
        bound_logger.info("alert_scheduler_started")
        for target_tenant_id, target_unit_id in targets:
            for generator_cls in self._select_generators(domain_filter):
                execution = await self._run_generator(
                    scheduler_run_id=scheduler_run_id,
                    tenant_id=target_tenant_id,
                    unidade_produtiva_id=target_unit_id,
                    generator_cls=generator_cls,
                    dry_run=dry_run,
                )
                self._accumulate(result, execution)
                bound_logger.bind(
                    tenant_id=str(target_tenant_id),
                    unidade_produtiva_id=str(target_unit_id) if target_unit_id else None,
                    domain=execution.domain.value,
                    generator_name=execution.generator_name,
                    status=execution.status,
                    duration_ms=execution.duration_ms,
                    created=execution.created,
                    updated=execution.updated,
                    ignored=execution.ignored,
                    skipped=execution.skipped,
                    warnings=execution.warnings,
                    errors=execution.errors,
                ).info("alert_scheduler_generator_finished")
        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(timezone.utc)  # noqa: UP017
        bound_logger.bind(
            generators_executed=result.generators_executed,
            alerts_created=result.alerts_created,
            alerts_updated=result.alerts_updated,
            alerts_ignored=result.alerts_ignored,
            alerts_skipped=result.alerts_skipped,
            warnings=result.warnings,
            errors=result.errors,
            duration_ms=result.duration_ms,
        ).info("alert_scheduler_finished")
        return result

    async def _run_generator(
        self,
        *,
        scheduler_run_id: UUID,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        generator_cls: type[BaseAlertGenerator],
        dry_run: bool,
    ) -> AlertSchedulerExecution:
        context = self._build_context(
            scheduler_run_id=scheduler_run_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            generator_cls=generator_cls,
            dry_run=dry_run,
        )
        generator = generator_cls(self.session, tenant_id)
        started_at = datetime.now(timezone.utc)  # noqa: UP017
        try:
            if dry_run:
                async with self.session.begin_nested() as nested:
                    try:
                        result = await self.runner.execute(generator, context)
                    finally:
                        await nested.rollback()
                        self.session.expire_all()
            else:
                result = await self.runner.execute(generator, context)
            status = self._execution_status(result, dry_run)
            return self._to_execution(
                tenant_id=tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                generator_cls=generator_cls,
                result=result,
                status=status,
            )
        except Exception as exc:  # pragma: no cover - defensive isolation
            # Sem rollback aqui, uma falha de flush (ex: IntegrityError) deixa a
            # sessão compartilhada em PendingRollbackError — todo generator/tenant
            # seguinte no mesmo run_scheduled_alerts falha em cascata com o mesmo
            # erro genérico, mascarando a causa raiz real. Confirmado em produção
            # (2026-08-14): FK violation num alerta de campo derrubou o generator
            # de pecuária do mesmo tenant.
            try:
                await self.session.rollback()
            except Exception:  # pragma: no cover - defensive isolation
                pass
            logger.bind(
                component="alert_scheduler_service",
                scheduler_run_id=str(scheduler_run_id),
                tenant_id=str(tenant_id),
                unidade_produtiva_id=str(unidade_produtiva_id) if unidade_produtiva_id else None,
                generator_name=getattr(generator_cls, "generator_name", generator_cls.__name__),
            ).exception("alert_scheduler_generator_failed")
            return self._failed_execution(
                tenant_id=tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                generator_cls=generator_cls,
                started_at=started_at,
                exc=exc,
            )

    async def _resolve_targets(
        self,
        tenant_id: UUID | None,
        unidade_produtiva_id: UUID | None,
    ) -> list[tuple[UUID, UUID | None]]:
        if tenant_id is not None:
            return [(tenant_id, unidade_produtiva_id)]
        if unidade_produtiva_id is not None:
            tenant = await self._tenant_for_unit(unidade_produtiva_id)
            if tenant is None:
                return []
            return [(tenant, unidade_produtiva_id)]
        return await self._active_tenants()

    async def _active_tenants(self) -> list[tuple[UUID, UUID | None]]:
        stmt = select(Tenant.id).where(Tenant.ativo.is_(True))
        rows = await self.session.execute(stmt)
        return [(tenant_id, None) for tenant_id in rows.scalars().all()]

    async def _tenant_for_unit(self, unidade_produtiva_id: UUID) -> UUID | None:
        stmt = select(UnidadeProdutiva.tenant_id).where(UnidadeProdutiva.id == unidade_produtiva_id)
        row = await self.session.execute(stmt)
        return row.scalar_one_or_none()

    def _select_generators(self, domains: set[str] | None) -> tuple[type[BaseAlertGenerator], ...]:
        generators = self.registry.find_scheduled_generators()
        if domains is None:
            return generators
        return tuple(
            generator_cls
            for generator_cls in generators
            if self._domain_value(getattr(generator_cls, "domain", None)) in domains
        )

    @staticmethod
    def _normalize_domains(domains: list[str] | None) -> set[str] | None:
        if domains is None:
            return None
        values = {domain.upper() for domain in domains if domain.strip()}
        return values or None

    @staticmethod
    def _domain_value(domain: Domain | str | None) -> str | None:
        if domain is None:
            return None
        if hasattr(domain, "value"):
            return str(domain.value)
        return str(domain)

    @staticmethod
    def _execution_status(result: AlertGeneratorResult, dry_run: bool) -> str:
        if result.errors > 0:
            return "failed"
        if dry_run:
            return "dry_run"
        return "success"

    @staticmethod
    def _build_context(
        *,
        scheduler_run_id: UUID,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        generator_cls: type[BaseAlertGenerator],
        dry_run: bool,
    ) -> AlertGeneratorContext:
        return AlertGeneratorContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            reason="scheduled",
            scope="scheduled",
            dry_run=dry_run,
            metadata={
                "scheduler_run_id": str(scheduler_run_id),
                "generator_name": getattr(generator_cls, "generator_name", generator_cls.__name__),
                "domain": AlertSchedulerService._domain_value(
                    getattr(generator_cls, "domain", None)
                ),
                "execution_modes": list(getattr(generator_cls, "execution_modes", ())),
            },
        )

    @staticmethod
    def _to_execution(
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        generator_cls: type[BaseAlertGenerator],
        result: AlertGeneratorResult,
        status: str,
    ) -> AlertSchedulerExecution:
        return AlertSchedulerExecution(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=generator_cls.domain or Domain.SYSTEM,
            generator_name=(
                result.generator_name
                or getattr(generator_cls, "generator_name", generator_cls.__name__)
            ),
            status=status,
            created=result.created,
            updated=result.updated,
            ignored=result.ignored,
            skipped=result.skipped,
            warnings=result.warnings,
            errors=result.errors,
            duration_ms=result.duration_ms,
            metadata=result.metadata,
        )

    @staticmethod
    def _failed_execution(
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        generator_cls: type[BaseAlertGenerator],
        started_at: datetime,
        exc: Exception,
    ) -> AlertSchedulerExecution:
        finished_at = datetime.now(timezone.utc)  # noqa: UP017
        return AlertSchedulerExecution(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=generator_cls.domain or Domain.SYSTEM,
            generator_name=getattr(
                generator_cls,
                "generator_name",
                generator_cls.__name__,
            ),
            status="failed",
            errors=1,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            metadata={
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            },
        )

    @staticmethod
    def _accumulate(result: AlertSchedulerResult, execution: AlertSchedulerExecution) -> None:
        result.generators_executed += 1
        result.alerts_created += execution.created
        result.alerts_updated += execution.updated
        result.alerts_ignored += execution.ignored
        result.alerts_skipped += execution.skipped
        result.warnings += execution.warnings
        result.errors += execution.errors
        result.executions.append(execution)


async def run_scheduled_alerts(
    session: AsyncSession,
    tenant_id: UUID | None = None,
    unidade_produtiva_id: UUID | None = None,
    domains: list[str] | None = None,
    dry_run: bool = False,
) -> AlertSchedulerResult:
    """Convenience helper for internal/manual scheduled execution."""

    return await AlertSchedulerService(session).run_scheduled_alerts(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        domains=domains,
        dry_run=dry_run,
    )
