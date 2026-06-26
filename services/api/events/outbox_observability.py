from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .outbox_metrics import (
    OutboxHealthReport,
    OutboxMetrics,
    evaluate_outbox_health,
)
from .outbox_model import DomainEventOutbox

UTC = timezone.utc  # noqa: UP017


@dataclass(slots=True)
class OutboxBacklogSnapshot:
    """Operational snapshot of the outbox backlog."""

    tenant_id: UUID | None
    event_type: str | None
    pending: int = 0
    processing: int = 0
    failed: int = 0
    dead_letter: int = 0
    processed: int = 0
    total: int = 0
    retries_seen: int = 0
    by_event_type: dict[str, int] = field(default_factory=dict)
    by_tenant: dict[str, int] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def current_backlog(self) -> int:
        """Return the backlog size that still needs operational attention."""

        return self.pending + self.processing + self.failed

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot without exposing payload content."""

        return {
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "event_type": self.event_type,
            "pending": self.pending,
            "processing": self.processing,
            "failed": self.failed,
            "dead_letter": self.dead_letter,
            "processed": self.processed,
            "total": self.total,
            "retries_seen": self.retries_seen,
            "current_backlog": self.current_backlog,
            "by_event_type": dict(self.by_event_type),
            "by_tenant": dict(self.by_tenant),
            "generated_at": self.generated_at.isoformat(),
        }


async def collect_outbox_backlog_snapshot(
    session: AsyncSession,
    *,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
) -> OutboxBacklogSnapshot:
    """Collect a safe operational snapshot of the outbox backlog."""

    status_counts = await _query_status_counts(session, tenant_id=tenant_id, event_type=event_type)
    event_type_counts = await _query_event_type_counts(
        session,
        tenant_id=tenant_id,
        event_type=event_type,
    )
    tenant_counts = await _query_tenant_counts(
        session,
        tenant_id=tenant_id,
        event_type=event_type,
    )
    retries_seen = await _query_retry_counts(
        session,
        tenant_id=tenant_id,
        event_type=event_type,
    )
    return OutboxBacklogSnapshot(
        tenant_id=tenant_id,
        event_type=event_type,
        pending=status_counts["pending"],
        processing=status_counts["processing"],
        failed=status_counts["failed"],
        dead_letter=status_counts["dead_letter"],
        processed=status_counts["processed"],
        total=sum(status_counts.values()),
        retries_seen=retries_seen,
        by_event_type=event_type_counts,
        by_tenant=tenant_counts,
    )


async def collect_outbox_metrics(
    session: AsyncSession,
    *,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
    base_metrics: OutboxMetrics | None = None,
) -> OutboxMetrics:
    """Collect operational metrics using the current backlog snapshot."""

    snapshot = await collect_outbox_backlog_snapshot(
        session,
        tenant_id=tenant_id,
        event_type=event_type,
    )
    metrics = base_metrics.clone() if base_metrics is not None else OutboxMetrics(
        started_at=snapshot.generated_at,
    )
    metrics.apply_snapshot(snapshot)
    return metrics


async def collect_outbox_health(
    session: AsyncSession,
    *,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
    base_metrics: OutboxMetrics | None = None,
) -> OutboxHealthReport:
    """Collect a health report for the outbox pipeline."""

    snapshot = await collect_outbox_backlog_snapshot(
        session,
        tenant_id=tenant_id,
        event_type=event_type,
    )
    metrics = base_metrics.clone() if base_metrics is not None else OutboxMetrics(
        started_at=snapshot.generated_at,
    )
    metrics.apply_snapshot(snapshot)
    report = evaluate_outbox_health(metrics)
    report.backlog = snapshot.current_backlog
    report.pending = snapshot.pending
    report.processing = snapshot.processing
    report.failed = snapshot.failed
    report.processed = snapshot.processed
    report.retries_seen = snapshot.retries_seen
    report.metrics = metrics.to_dict()
    return report


def render_outbox_metrics_text(metrics: OutboxMetrics) -> str:
    """Render a human-friendly metrics snapshot."""

    last_success = metrics.last_success_at.isoformat() if metrics.last_success_at else "none"
    last_error = metrics.last_error or "none"
    return (
        "Outbox Worker Metrics\n\n"
        f"Uptime: {metrics.uptime_seconds}s\n"
        f"Cycles: {metrics.cycles}\n"
        f"Batches processed: {metrics.batches_processed}\n"
        f"Events processed: {metrics.events_processed}\n"
        f"Events failed: {metrics.events_failed}\n"
        f"Errors: {metrics.errors}\n"
        f"Backlog: {metrics.current_backlog}\n"
        f"Retries: {metrics.retries_seen}\n"
        f"Throughput/min: {metrics.throughput_per_minute:.2f}\n"
        f"Average batch size: {metrics.average_batch_size:.2f}\n"
        f"Last success: {last_success}\n"
        f"Last error: {last_error}\n"
    )


def render_outbox_metrics_json(metrics: OutboxMetrics) -> str:
    """Render a JSON snapshot for machine consumers."""

    return json.dumps(metrics.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def render_outbox_health_text(report: OutboxHealthReport) -> str:
    """Render a human-friendly health summary."""

    return report.to_text()


async def _query_status_counts(
    session: AsyncSession,
    *,
    tenant_id: UUID | None,
    event_type: str | None,
) -> dict[str, int]:
    counts = {"pending": 0, "processing": 0, "failed": 0, "dead_letter": 0, "processed": 0}
    stmt = select(DomainEventOutbox.status, func.count()).group_by(DomainEventOutbox.status)
    if tenant_id is not None:
        stmt = stmt.where(DomainEventOutbox.tenant_id == tenant_id)
    if event_type is not None:
        stmt = stmt.where(DomainEventOutbox.event_type == event_type)
    rows = await session.execute(stmt)
    for status, total in rows.all():
        counts[str(status)] = int(total)
    return counts


async def _query_event_type_counts(
    session: AsyncSession,
    *,
    tenant_id: UUID | None,
    event_type: str | None,
) -> dict[str, int]:
    stmt = select(DomainEventOutbox.event_type, func.count()).group_by(DomainEventOutbox.event_type)
    if tenant_id is not None:
        stmt = stmt.where(DomainEventOutbox.tenant_id == tenant_id)
    if event_type is not None:
        stmt = stmt.where(DomainEventOutbox.event_type == event_type)
    rows = await session.execute(stmt)
    return {str(event): int(total) for event, total in rows.all()}


async def _query_tenant_counts(
    session: AsyncSession,
    *,
    tenant_id: UUID | None,
    event_type: str | None,
) -> dict[str, int]:
    stmt = select(DomainEventOutbox.tenant_id, func.count()).group_by(DomainEventOutbox.tenant_id)
    if tenant_id is not None:
        stmt = stmt.where(DomainEventOutbox.tenant_id == tenant_id)
    if event_type is not None:
        stmt = stmt.where(DomainEventOutbox.event_type == event_type)
    rows = await session.execute(stmt)
    return {str(tenant): int(total) for tenant, total in rows.all()}


async def _query_retry_counts(
    session: AsyncSession,
    *,
    tenant_id: UUID | None,
    event_type: str | None,
) -> int:
    stmt = select(
        func.coalesce(
            func.sum(
                case(
                    (DomainEventOutbox.attempts > 1, DomainEventOutbox.attempts - 1),
                    else_=0,
                )
            ),
            0,
        )
    )
    if tenant_id is not None:
        stmt = stmt.where(DomainEventOutbox.tenant_id == tenant_id)
    if event_type is not None:
        stmt = stmt.where(DomainEventOutbox.event_type == event_type)
    rows = await session.execute(stmt)
    value = rows.scalar_one_or_none()
    return int(value or 0)
