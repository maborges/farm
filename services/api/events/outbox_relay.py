from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .outbox_model import DomainEventOutbox, DomainEventOutboxStatus
from .outbox_service import DomainEventOutboxService
from .publisher import EventPublisherResult, publish_domain_event
from .registry import EventSubscriberRegistry, event_subscriber_registry


class DomainEventOutboxRelayResult(BaseModel):  # type: ignore[misc]
    """Canonical summary for a relay execution."""

    relay_id: UUID
    total_claimed: int = 0
    processed: int = 0
    failed: int = 0
    dead_letter: int = 0
    duration_ms: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    executions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class DomainEventOutboxRelay:
    """Programmatic relay that fans out persisted outbox events through EventPublisher."""

    def __init__(
        self,
        session: AsyncSession,
        registry: EventSubscriberRegistry | None = None,
        service: DomainEventOutboxService | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or event_subscriber_registry
        self.service = service or DomainEventOutboxService(session)

    async def run_once(
        self,
        batch_size: int = 50,
        tenant_id: UUID | None = None,
        relay_id: UUID | str | None = None,
        event_type: str | None = None,
    ) -> DomainEventOutboxRelayResult:
        """Claim and process a single batch of due outbox rows."""

        started_at = datetime.now(timezone.utc)  # noqa: UP017
        start = perf_counter()
        relay_uuid = relay_id if isinstance(relay_id, UUID) else uuid4()
        relay_ref = str(relay_id or relay_uuid)
        result = DomainEventOutboxRelayResult(relay_id=relay_uuid, started_at=started_at)
        bound_logger = logger.bind(
            component="domain_event_outbox_relay",
            relay_id=relay_ref,
            tenant_id=str(tenant_id) if tenant_id else None,
        )
        bound_logger.info("domain_event_outbox_relay_started")
        try:
            claimed = await self.service.claim_batch(
                batch_size=batch_size,
                tenant_id=tenant_id,
                relay_id=relay_ref,
                event_type=event_type,
            )
            result.total_claimed = len(claimed)
            for row in claimed:
                execution = await self._process_row(row)
                result.executions.append(execution)
                if execution["status"] == DomainEventOutboxStatus.PROCESSED.value:
                    result.processed += 1
                elif execution["status"] == DomainEventOutboxStatus.DEAD_LETTER.value:
                    result.dead_letter += 1
                else:
                    result.failed += 1
                bound_logger.bind(**execution).info("domain_event_outbox_relay_row_finished")
            await self.session.commit()
        except Exception as exc:  # pragma: no cover - defensive isolation
            await self.session.rollback()
            bound_logger.bind(
                exception_type=exc.__class__.__name__, exception_message=str(exc)
            ).exception("domain_event_outbox_relay_failed")
            raise

        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(timezone.utc)  # noqa: UP017
        bound_logger.bind(
            total_claimed=result.total_claimed,
            processed=result.processed,
            failed=result.failed,
            dead_letter=result.dead_letter,
            duration_ms=result.duration_ms,
        ).info("domain_event_outbox_relay_finished")
        return result

    async def _process_row(self, row: DomainEventOutbox) -> dict[str, Any]:
        event = self.service.rebuild_domain_event(row)
        started_at = datetime.now(timezone.utc)  # noqa: UP017
        try:
            if getattr(row, "tenant_id", None) is not None and hasattr(
                self.service, "_set_rls_context"
            ):
                await self.service._set_rls_context(row.tenant_id)
            publisher_result = await publish_domain_event(
                event,
                session=self.session,
                registry=self.registry,
            )
            if publisher_result.errors:
                updated = await self.service.mark_failed(
                    row,
                    f"publisher_errors={publisher_result.errors}",
                )
                return self._execution_payload(updated, started_at, publisher_result)
            updated = await self.service.mark_processed(row)
            return self._execution_payload(updated, started_at, publisher_result)
        except Exception as exc:  # pragma: no cover - defensive isolation
            updated = await self.service.mark_failed(row, exc)
            return self._execution_payload(updated, started_at, None, exc)

    @staticmethod
    def _execution_payload(
        row: DomainEventOutbox,
        started_at: datetime,
        publisher_result: EventPublisherResult | None,
        exc: Exception | None = None,
    ) -> dict[str, Any]:
        finished_at = datetime.now(timezone.utc)  # noqa: UP017
        return {
            "outbox_id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "event_type": row.event_type,
            "status": row.status,
            "attempts": row.attempts,
            "idempotency_key": row.idempotency_key,
            "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
            "errors": publisher_result.errors if publisher_result else 1,
            "warnings": publisher_result.warnings if publisher_result else 0,
            "exception_type": exc.__class__.__name__ if exc else None,
            "exception_message": str(exc) if exc else None,
        }
