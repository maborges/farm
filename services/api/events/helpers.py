from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from .base import DomainEvent
from .publisher import EventPublisherResult, publish_domain_event
from .registry import EventSubscriberRegistry


async def publish_domain_event_safe(
    event: DomainEvent,
    session: AsyncSession | None = None,
    registry: EventSubscriberRegistry | None = None,
    *,
    logger_context: dict[str, Any] | None = None,
) -> EventPublisherResult | None:
    """Publish a domain event and swallow non-fatal failures with structured logs."""

    start = perf_counter()
    started_at = datetime.now(timezone.utc)  # noqa: UP017
    context: dict[str, Any] = {
        "component": "domain_event_publisher",
        "event_id": str(event.event_id),
        "event_type": event.event_type,
        "tenant_id": str(event.tenant_id),
        "unidade_produtiva_id": str(event.unidade_produtiva_id)
        if event.unidade_produtiva_id
        else None,
        "correlation_id": str(event.correlation_id) if event.correlation_id else None,
        "causation_id": str(event.causation_id) if event.causation_id else None,
        "entity_type": event.entity_type,
        "entity_id": str(event.entity_id) if event.entity_id else None,
    }
    context.update(logger_context or {})
    bound_logger = logger.bind(**context)
    bound_logger.info("domain_event_publish_started")
    try:
        result = await publish_domain_event(event, session=session, registry=registry)
    except Exception as exc:  # pragma: no cover - defensive isolation
        finished_at = datetime.now(timezone.utc)  # noqa: UP017
        bound_logger.bind(
            status="failed",
            errors=1,
            warnings=0,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            exception_type=exc.__class__.__name__,
            exception_message=str(exc),
        ).exception("domain_event_publish_failed")
        return None

    status = "partial" if result.errors else "published"
    created = sum(execution.created for execution in result.executions) if result.executions else 0
    updated = sum(execution.updated for execution in result.executions) if result.executions else 0
    ignored = sum(execution.ignored for execution in result.executions) if result.executions else 0
    skipped = sum(execution.skipped for execution in result.executions) if result.executions else 0
    bound_logger.bind(
        status=status,
        created=created,
        updated=updated,
        ignored=ignored,
        skipped=skipped,
        warnings=result.warnings,
        errors=result.errors,
        duration_ms=int((perf_counter() - start) * 1000),
    ).info("domain_event_publish_finished")
    return result
