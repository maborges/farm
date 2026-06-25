from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import UUID

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .base import DomainEvent, EventSubscriber, EventSubscriberResult
from .registry import EventSubscriberRegistry, event_subscriber_registry


class EventSubscriberExecution(BaseModel):
    """Per-subscriber execution summary for a published event."""

    event_id: UUID
    event_type: str
    subscriber_name: str
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


class EventPublisherResult(BaseModel):
    """Aggregate result for a single domain event publication."""

    event_id: UUID
    event_type: str
    total_subscribers: int = 0
    executed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    warnings: int = 0
    errors: int = 0
    duration_ms: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    executions: list[EventSubscriberExecution] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class EventPublisher:
    """In-memory event publisher that fans out to registered subscribers."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        registry: EventSubscriberRegistry | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or event_subscriber_registry

    async def publish(self, event: DomainEvent) -> EventPublisherResult:
        """Publish a domain event to all eligible subscribers."""

        started_at = datetime.now(timezone.utc)  # noqa: UP017
        start = perf_counter()
        subscribers = self.registry.find_by_event_type(event.event_type)
        result = EventPublisherResult(
            event_id=event.event_id,
            event_type=event.event_type,
            total_subscribers=len(subscribers),
            started_at=started_at,
        )
        bound_logger = logger.bind(
            component="event_publisher",
            event_id=str(event.event_id),
            event_type=event.event_type,
            tenant_id=str(event.tenant_id),
            unidade_produtiva_id=str(event.unidade_produtiva_id)
            if event.unidade_produtiva_id
            else None,
        )
        bound_logger.info("event_publisher_started")
        for subscriber_cls in subscribers:
            execution = await self._run_subscriber(event, subscriber_cls)
            self._accumulate(result, execution)
            self._log_execution(bound_logger, execution)
        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(timezone.utc)  # noqa: UP017
        bound_logger.bind(
            total_subscribers=result.total_subscribers,
            executed=result.executed,
            succeeded=result.succeeded,
            failed=result.failed,
            skipped=result.skipped,
            warnings=result.warnings,
            errors=result.errors,
            duration_ms=result.duration_ms,
        ).info("event_publisher_finished")
        return result

    async def _run_subscriber(
        self,
        event: DomainEvent,
        subscriber_cls: type[EventSubscriber],
    ) -> EventSubscriberExecution:
        subscriber = subscriber_cls(self.session)
        started_at = datetime.now(timezone.utc)  # noqa: UP017
        try:
            result = await subscriber.handle(event)
            status = result.status or "success"
            return self._to_execution(result, status)
        except Exception as exc:  # pragma: no cover - defensive isolation
            logger.bind(
                component="event_publisher",
                event_id=str(event.event_id),
                event_type=event.event_type,
                subscriber_name=getattr(subscriber_cls, "subscriber_name", subscriber_cls.__name__),
            ).exception("event_subscriber_failed")
            finished_at = datetime.now(timezone.utc)  # noqa: UP017
            return EventSubscriberExecution(
                event_id=event.event_id,
                event_type=event.event_type,
                subscriber_name=getattr(
                    subscriber_cls,
                    "subscriber_name",
                    subscriber_cls.__name__,
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
    def _to_execution(result: EventSubscriberResult, status: str) -> EventSubscriberExecution:
        return EventSubscriberExecution(
            event_id=result.event_id,
            event_type=result.event_type,
            subscriber_name=result.subscriber_name,
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
    def _accumulate(result: EventPublisherResult, execution: EventSubscriberExecution) -> None:
        result.executed += 1
        result.succeeded += 1 if execution.status == "success" else 0
        result.failed += 1 if execution.status == "failed" else 0
        result.skipped += execution.skipped
        result.warnings += execution.warnings
        result.errors += execution.errors
        result.executions.append(execution)

    @staticmethod
    def _log_execution(bound_logger, execution: EventSubscriberExecution) -> None:
        bound_logger.bind(
            subscriber_name=execution.subscriber_name,
            status=execution.status,
            duration_ms=execution.duration_ms,
            errors=execution.errors,
            warnings=execution.warnings,
        ).info("event_publisher_subscriber_finished")


async def publish_domain_event(
    event: DomainEvent,
    session: AsyncSession | None = None,
    registry: EventSubscriberRegistry | None = None,
) -> EventPublisherResult:
    """Convenience helper for in-memory domain event publication."""

    return await EventPublisher(session=session, registry=registry).publish(event)
