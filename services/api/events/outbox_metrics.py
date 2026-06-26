from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

UTC = timezone.utc  # noqa: UP017


class OutboxHealthStatus(str, Enum):
    """Operational health states for the outbox pipeline."""

    OK = "OK"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class OutboxHealthThresholds:
    """Defensive thresholds used to classify worker health."""

    healthy_backlog_max: int = 10
    degraded_backlog_max: int = 50
    critical_backlog_max: int = 200
    recent_error_window_seconds: int = 300
    stale_success_window_seconds: int = 900
    degraded_retry_threshold: int = 5
    critical_retry_threshold: int = 20
    critical_error_threshold: int = 3


DEFAULT_OUTBOX_HEALTH_THRESHOLDS = OutboxHealthThresholds()


@dataclass(slots=True)
class OutboxMetrics:
    """In-memory operational metrics for the outbox worker."""

    started_at: datetime
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None
    cycles: int = 0
    batches_processed: int = 0
    events_processed: int = 0
    events_failed: int = 0
    errors: int = 0
    retries_seen: int = 0
    current_backlog: int = 0
    last_batch_size: int = 0
    max_batch_size: int = 0
    _batch_size_total: int = field(default=0, repr=False, compare=False)

    @property
    def uptime_seconds(self) -> int:
        """Return the runtime uptime in seconds."""

        return max(int((datetime.now(UTC) - self.started_at).total_seconds()), 0)

    @property
    def average_batch_size(self) -> float:
        """Return the average batch size observed so far."""

        if self.batches_processed == 0:
            return 0.0
        return self._batch_size_total / self.batches_processed

    @property
    def throughput_per_minute(self) -> float:
        """Return an approximate throughput in events per minute."""

        uptime = max(self.uptime_seconds, 1)
        return (self.events_processed / uptime) * 60.0

    def clone(self) -> OutboxMetrics:
        """Return a detached copy of the current metrics snapshot."""

        return replace(self)

    def record_cycle(
        self,
        *,
        batches: int,
        batch_size: int,
        processed: int,
        failed: int = 0,
        backlog: int = 0,
        retries_seen: int | None = None,
    ) -> None:
        """Update metrics after a successful worker cycle."""

        now = datetime.now(UTC)
        self.cycles += 1
        self.batches_processed += batches
        self.events_processed += processed
        self.events_failed += failed
        self.last_success_at = now
        self.last_error = None
        self.last_error_at = None
        self.last_batch_size = batch_size
        self.max_batch_size = max(self.max_batch_size, batch_size)
        self._batch_size_total += batch_size
        self.current_backlog = backlog
        if retries_seen is not None:
            self.retries_seen = retries_seen

    def record_error(self, error: str, backlog: int | None = None) -> None:
        """Update metrics after a failed worker cycle."""

        now = datetime.now(UTC)
        self.cycles += 1
        self.errors += 1
        self.last_error = error
        self.last_error_at = now
        if backlog is not None:
            self.current_backlog = backlog

    def apply_snapshot(self, snapshot: Any) -> None:
        """Merge an outbox backlog snapshot into the metrics state."""

        self.current_backlog = int(getattr(snapshot, "current_backlog", self.current_backlog))
        self.retries_seen = int(getattr(snapshot, "retries_seen", self.retries_seen))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the metrics to a plain dictionary."""

        return {
            "started_at": self.started_at.isoformat(),
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "last_error": self.last_error,
            "cycles": self.cycles,
            "batches_processed": self.batches_processed,
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "errors": self.errors,
            "retries_seen": self.retries_seen,
            "current_backlog": self.current_backlog,
            "last_batch_size": self.last_batch_size,
            "max_batch_size": self.max_batch_size,
            "average_batch_size": self.average_batch_size,
            "throughput_per_minute": self.throughput_per_minute,
            "uptime_seconds": self.uptime_seconds,
        }


@dataclass(slots=True)
class OutboxHealthReport:
    """Operational health summary for the outbox pipeline."""

    status: OutboxHealthStatus
    backlog: int
    pending: int
    processing: int
    failed: int
    processed: int
    retries_seen: int
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error: str | None
    recommendation: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the health report to a plain dictionary."""

        return {
            "status": self.status.value,
            "backlog": self.backlog,
            "pending": self.pending,
            "processing": self.processing,
            "failed": self.failed,
            "processed": self.processed,
            "retries_seen": self.retries_seen,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "last_error": self.last_error,
            "recommendation": self.recommendation,
            "generated_at": self.generated_at.isoformat(),
            "metrics": dict(self.metrics),
        }

    def to_text(self) -> str:
        """Render a human-friendly health summary."""

        last_success = self.last_success_at.isoformat() if self.last_success_at else "none"
        last_error = self.last_error or "none"
        return (
            "Outbox Worker Health\n\n"
            f"Status: {self.status.value}\n"
            f"Backlog: {self.backlog}\n"
            f"Retries: {self.retries_seen}\n"
            f"Pending: {self.pending}\n"
            f"Last success: {last_success}\n"
            f"Last error: {last_error}\n\n"
            "Recommendation:\n"
            f"{self.recommendation}\n"
        )


OBSERVABILITY_METRICS = OutboxMetrics(started_at=datetime.now(UTC))


def get_observability_metrics() -> OutboxMetrics:
    """Return the current in-memory metrics object."""

    return OBSERVABILITY_METRICS


def reset_observability_metrics(started_at: datetime | None = None) -> OutboxMetrics:
    """Reset the in-memory metrics state."""

    global OBSERVABILITY_METRICS
    OBSERVABILITY_METRICS = OutboxMetrics(started_at=started_at or datetime.now(UTC))
    return OBSERVABILITY_METRICS


def build_outbox_metrics(
    base: OutboxMetrics | None = None,
    snapshot: Any | None = None,
) -> OutboxMetrics:
    """Build a detached metrics snapshot from the current state."""

    metrics = base.clone() if base is not None else OutboxMetrics(started_at=datetime.now(UTC))
    if snapshot is not None:
        metrics.apply_snapshot(snapshot)
    return metrics


def evaluate_outbox_health(
    metrics: OutboxMetrics,
    thresholds: OutboxHealthThresholds = DEFAULT_OUTBOX_HEALTH_THRESHOLDS,
) -> OutboxHealthReport:
    """Classify the outbox pipeline health from the current metrics."""

    now = datetime.now(UTC)
    recent_error = _is_recent(metrics.last_error_at, now, thresholds.recent_error_window_seconds)
    stale_success = _is_stale(metrics.last_success_at, now, thresholds.stale_success_window_seconds)
    backlog = metrics.current_backlog
    if _has_no_observability_data(metrics):
        return _build_health_report(
            OutboxHealthStatus.UNKNOWN,
            metrics,
            recommendation="Collect more data before acting.",
        )
    if (
        backlog >= thresholds.critical_backlog_max
        or metrics.retries_seen >= thresholds.critical_retry_threshold
        or (metrics.errors >= thresholds.critical_error_threshold and stale_success)
    ):
        return _build_health_report(
            OutboxHealthStatus.CRITICAL,
            metrics,
            recommendation="Investigate failures and scale the worker capacity.",
        )
    if (
        backlog > thresholds.healthy_backlog_max
        or backlog >= thresholds.degraded_backlog_max
        or recent_error
        or metrics.retries_seen >= thresholds.degraded_retry_threshold
        or stale_success
    ):
        return _build_health_report(
            OutboxHealthStatus.DEGRADED,
            metrics,
            recommendation="Inspect backlog growth and recent errors.",
        )
    return _build_health_report(
        OutboxHealthStatus.OK,
        metrics,
        recommendation="No action required.",
    )


def _build_health_report(
    status: OutboxHealthStatus,
    metrics: OutboxMetrics,
    *,
    recommendation: str,
) -> OutboxHealthReport:
    return OutboxHealthReport(
        status=status,
        backlog=metrics.current_backlog,
        pending=metrics.current_backlog,
        processing=0,
        failed=metrics.events_failed,
        processed=metrics.events_processed,
        retries_seen=metrics.retries_seen,
        last_success_at=metrics.last_success_at,
        last_error_at=metrics.last_error_at,
        last_error=metrics.last_error,
        recommendation=recommendation,
        metrics=metrics.to_dict(),
    )


def _has_no_observability_data(metrics: OutboxMetrics) -> bool:
    return (
        metrics.cycles == 0
        and metrics.events_processed == 0
        and metrics.events_failed == 0
        and metrics.errors == 0
        and metrics.current_backlog == 0
        and metrics.last_error is None
        and metrics.last_success_at is None
    )


def _is_recent(timestamp: datetime | None, now: datetime, window_seconds: int) -> bool:
    if timestamp is None:
        return False
    return (now - timestamp) <= timedelta(seconds=window_seconds)


def _is_stale(timestamp: datetime | None, now: datetime, window_seconds: int) -> bool:
    if timestamp is None:
        return True
    return (now - timestamp) >= timedelta(seconds=window_seconds)
