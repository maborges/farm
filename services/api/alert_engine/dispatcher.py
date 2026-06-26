from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
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
from events.base import DomainEvent as AlertDomainEvent


class AlertDispatchExecution(BaseModel):
    """Per-generator execution summary for a dispatched domain event."""

    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: Domain
    event_type: str
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


class AlertDispatcherResult(BaseModel):
    """Aggregate result for a single Alert Domain Event dispatch."""

    dispatch_id: UUID
    event_id: UUID
    correlation_id: UUID | None = None
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
    executions: list[AlertDispatchExecution] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AlertDispatcherService:
    """Post-commit coordinator for Alert Engine event-driven execution."""

    def __init__(
        self,
        session: AsyncSession,
        registry: AlertGeneratorRegistry | None = None,
        runner: AlertGeneratorRunner | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or alert_generator_registry
        self.runner = runner or AlertGeneratorRunner()

    async def dispatch(self, event: AlertDomainEvent) -> AlertDispatcherResult:
        """Dispatch a domain event to all eligible generators.

        Args:
            event: Canonical post-commit event envelope.

        Returns:
            Consolidated dispatch result with per-generator executions.
        """

        dispatch_id = uuid4()
        started_at = datetime.now(timezone.utc)  # noqa: UP017
        start = perf_counter()
        result = AlertDispatcherResult(
            dispatch_id=dispatch_id,
            event_id=event.event_id,
            correlation_id=event.correlation_id,
            started_at=started_at,
        )
        bound_logger = self._logger(event, dispatch_id)
        bound_logger.info("alert_dispatcher_started")
        for generator_cls in self._resolve_generators(event):
            execution = await self._run_generator(dispatch_id, event, generator_cls)
            self._accumulate(result, execution)
            self._log_execution(bound_logger, execution)
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
        ).info("alert_dispatcher_finished")
        return result

    async def _run_generator(
        self,
        dispatch_id: UUID,
        event: AlertDomainEvent,
        generator_cls: type[BaseAlertGenerator],
    ) -> AlertDispatchExecution:
        context = self._build_context(dispatch_id, event, generator_cls)
        generator = generator_cls(self.session, event.tenant_id)
        started_at = datetime.now(timezone.utc)  # noqa: UP017
        try:
            result = await self.runner.execute(generator, context)
            status = "failed" if result.errors > 0 else "success"
            return self._to_execution(event, generator_cls, result, status)
        except Exception as exc:  # pragma: no cover - defensive isolation
            logger.bind(
                component="alert_dispatcher_service",
                dispatch_id=str(dispatch_id),
                event_id=str(event.event_id),
                tenant_id=str(event.tenant_id),
                unidade_produtiva_id=(
                    str(event.unidade_produtiva_id) if event.unidade_produtiva_id else None
                ),
                correlation_id=str(event.correlation_id) if event.correlation_id else None,
                causation_id=str(event.causation_id) if event.causation_id else None,
                generator_name=getattr(
                    generator_cls,
                    "generator_name",
                    generator_cls.__name__,
                ),
            ).exception("alert_dispatcher_generator_failed")
            return self._failed_execution(event, generator_cls, started_at, exc)

    def _resolve_generators(self, event: AlertDomainEvent) -> tuple[type[BaseAlertGenerator], ...]:
        generators = self.registry.find_by_event_type(event.event_type)
        return tuple(
            generator_cls
            for generator_cls in generators
            if self._matches_domain(generator_cls, event.domain)
        )

    @staticmethod
    def _matches_domain(generator_cls: type[BaseAlertGenerator], domain: Domain) -> bool:
        generator_domain = getattr(generator_cls, "domain", None)
        return generator_domain is None or generator_domain == domain

    @staticmethod
    def _build_context(
        dispatch_id: UUID,
        event: AlertDomainEvent,
        generator_cls: type[BaseAlertGenerator],
    ) -> AlertGeneratorContext:
        metadata = dict(event.metadata)
        metadata.update(
            {
                "dispatch_id": str(dispatch_id),
                "event": event.model_dump(mode="json"),
                "generator_name": getattr(generator_cls, "generator_name", generator_cls.__name__),
            }
        )
        return AlertGeneratorContext(
            tenant_id=event.tenant_id,
            unidade_produtiva_id=event.unidade_produtiva_id,
            event_id=event.event_id,
            scope="event",
            reason="event_dispatch",
            metadata=metadata,
        )

    @staticmethod
    def _to_execution(
        event: AlertDomainEvent,
        generator_cls: type[BaseAlertGenerator],
        result: AlertGeneratorResult,
        status: str,
    ) -> AlertDispatchExecution:
        return AlertDispatchExecution(
            tenant_id=event.tenant_id,
            unidade_produtiva_id=event.unidade_produtiva_id,
            domain=event.domain,
            event_type=event.event_type,
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
        event: AlertDomainEvent,
        generator_cls: type[BaseAlertGenerator],
        started_at: datetime,
        exc: Exception,
    ) -> AlertDispatchExecution:
        finished_at = datetime.now(timezone.utc)  # noqa: UP017
        return AlertDispatchExecution(
            tenant_id=event.tenant_id,
            unidade_produtiva_id=event.unidade_produtiva_id,
            domain=event.domain,
            event_type=event.event_type,
            generator_name=getattr(generator_cls, "generator_name", generator_cls.__name__),
            status="failed",
            errors=1,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            metadata={
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            },
        )

    @staticmethod
    def _accumulate(result: AlertDispatcherResult, execution: AlertDispatchExecution) -> None:
        result.generators_executed += 1
        result.alerts_created += execution.created
        result.alerts_updated += execution.updated
        result.alerts_ignored += execution.ignored
        result.alerts_skipped += execution.skipped
        result.warnings += execution.warnings
        result.errors += execution.errors
        result.executions.append(execution)

    @staticmethod
    def _logger(event: AlertDomainEvent, dispatch_id: UUID):
        return logger.bind(
            component="alert_dispatcher_service",
            dispatch_id=str(dispatch_id),
            event_id=str(event.event_id),
            correlation_id=str(event.correlation_id) if event.correlation_id else None,
            causation_id=str(event.causation_id) if event.causation_id else None,
            tenant_id=str(event.tenant_id),
            unidade_produtiva_id=(
                str(event.unidade_produtiva_id) if event.unidade_produtiva_id else None
            ),
            domain=event.domain.value,
            event_type=event.event_type,
        )

    @staticmethod
    def _log_execution(bound_logger, execution: AlertDispatchExecution) -> None:
        bound_logger.bind(
            tenant_id=str(execution.tenant_id),
            unidade_produtiva_id=(
                str(execution.unidade_produtiva_id) if execution.unidade_produtiva_id else None
            ),
            domain=execution.domain.value,
            event_type=execution.event_type,
            generator_name=execution.generator_name,
            status=execution.status,
            duration_ms=execution.duration_ms,
            created=execution.created,
            updated=execution.updated,
            ignored=execution.ignored,
            skipped=execution.skipped,
            warnings=execution.warnings,
            errors=execution.errors,
        ).info("alert_dispatcher_generator_finished")


async def dispatch_alert_event(
    session: AsyncSession,
    event: AlertDomainEvent,
    registry: AlertGeneratorRegistry | None = None,
    runner: AlertGeneratorRunner | None = None,
) -> AlertDispatcherResult:
    """Convenience helper for programmatic post-commit dispatch."""

    return await AlertDispatcherService(session, registry=registry, runner=runner).dispatch(event)
