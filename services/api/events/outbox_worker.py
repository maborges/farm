from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import engine, get_db_session

from .outbox_metrics import OutboxMetrics, get_observability_metrics, reset_observability_metrics
from .outbox_model import DomainEventOutbox
from .outbox_observability import (
    collect_outbox_backlog_snapshot,
    collect_outbox_health,
    collect_outbox_metrics,
    render_outbox_health_text,
    render_outbox_metrics_json,
    render_outbox_metrics_text,
)
from .outbox_relay import DomainEventOutboxRelay, DomainEventOutboxRelayResult
from .outbox_service import DomainEventOutboxService

UTC = timezone.utc  # noqa: UP017

EXIT_OK = 0
EXIT_OPERATIONAL_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_LOCK_NOT_OBTAINED = 3
EXIT_UNEXPECTED_ERROR = 4
EXIT_INTERRUPTED = 130

COMMAND_RUN = "run"
COMMAND_STATUS = "status"
COMMAND_STATS = "stats"
COMMAND_HEALTH = "health"
COMMAND_METRICS = "metrics"
COMMANDS = (COMMAND_RUN, COMMAND_STATUS, COMMAND_STATS, COMMAND_HEALTH, COMMAND_METRICS)
DEFAULT_LOOP_INTERVAL_SECONDS = 10
DEFAULT_LOOP_BACKOFF_SECONDS = 5
DEFAULT_LOOP_MAX_BACKOFF_SECONDS = 60
DEFAULT_LOOP_HEARTBEAT_SECONDS = 60


class OutboxWorkerRunResult(BaseModel):  # type: ignore[misc]
    """Canonical summary for a worker execution."""

    worker_run_id: UUID
    command: str = COMMAND_RUN
    status: str = "completed"
    exit_code: int = EXIT_OK
    dry_run: bool = False
    total_batches: int = 0
    total_claimed: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_dead_letter: int = 0
    duration_ms: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    relay_runs: list[DomainEventOutboxRelayResult] = Field(default_factory=list)
    batch_runs: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class OutboxWorkerStatusResult(BaseModel):  # type: ignore[misc]
    """Canonical snapshot of outbox status counts."""

    worker_run_id: UUID
    command: str = COMMAND_STATUS
    exit_code: int = EXIT_OK
    tenant_id: UUID | None = None
    event_type: str | None = None
    pending: int = 0
    processing: int = 0
    failed: int = 0
    dead_letter: int = 0
    processed: int = 0
    total: int = 0
    backlog_estimated: int = 0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class OutboxWorkerStatsResult(BaseModel):  # type: ignore[misc]
    """Canonical aggregate for outbox statistics."""

    worker_run_id: UUID
    command: str = COMMAND_STATS
    exit_code: int = EXIT_OK
    tenant_id: UUID | None = None
    event_type: str | None = None
    total: int = 0
    backlog_estimated: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_event_type: dict[str, int] = Field(default_factory=dict)
    by_tenant: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


@dataclass(slots=True)
class WorkerStats:
    """In-memory runtime stats for the permanent worker loop."""

    started_at: datetime
    cycles: int = 0
    batches_processed: int = 0
    events_processed: int = 0
    errors: int = 0
    last_success: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    last_heartbeat_at: datetime | None = None

    @property
    def uptime(self) -> int:
        """Return uptime in seconds."""

        return int((datetime.now(UTC) - self.started_at).total_seconds())

    def mark_cycle(self, result: OutboxWorkerRunResult) -> None:
        """Update runtime stats after a successful worker cycle."""

        self.cycles += 1
        self.batches_processed += result.total_batches
        self.events_processed += result.total_processed
        self.last_success = datetime.now(UTC)
        self.last_error = None
        self.last_error_at = None

    def mark_error(self, error: str) -> None:
        """Update runtime stats after a failed worker cycle."""

        self.cycles += 1
        self.errors += 1
        self.last_error = error
        self.last_error_at = datetime.now(UTC)

    def heartbeat_payload(self) -> dict[str, Any]:
        """Return a serializable heartbeat snapshot."""

        return {
            "uptime": self.uptime,
            "cycles": self.cycles,
            "batches_processed": self.batches_processed,
            "events_processed": self.events_processed,
            "errors": self.errors,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
        }


def _normalize_argv(argv: list[str] | None) -> list[str]:
    args = list(argv or [])
    if not args:
        return [COMMAND_RUN]
    if args[0] in {"-h", "--help"}:
        return args
    if args[0] in COMMANDS:
        return args
    if args[0].startswith("-"):
        return [COMMAND_RUN, *args]
    return args


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _build_common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--tenant-id", type=str, default=None)
    parser.add_argument("--event-type", type=str, default=None)
    parser.add_argument("--verbose", action="store_true", default=False)
    return parser


def build_parser() -> argparse.ArgumentParser:
    """Build the operational CLI parser."""

    common = _build_common_parser()
    parser = argparse.ArgumentParser(
        prog="python -m events.outbox_worker",
        description="Operational CLI for the domain-event outbox worker",
        epilog=(
            "Commands: run, status, stats, health, metrics. "
            "Running without a command defaults to 'run'."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        COMMAND_RUN,
        parents=[common],
        help="Execute the relay in bounded batches",
    )
    run_parser.add_argument("--batch-size", type=_positive_int, default=50)
    run_parser.add_argument("--max-batches", type=_positive_int, default=1)
    run_parser.add_argument("--locked-by", type=str, default=None)
    run_parser.add_argument("--stop-on-error", action="store_true", default=False)
    run_parser.add_argument("--dry-run", action="store_true", default=False)
    run_parser.add_argument("--loop", action="store_true", default=False)
    run_parser.add_argument("--interval", type=_positive_int, default=DEFAULT_LOOP_INTERVAL_SECONDS)
    run_parser.add_argument("--backoff", type=_positive_int, default=DEFAULT_LOOP_BACKOFF_SECONDS)
    run_parser.add_argument(
        "--max-backoff",
        type=_positive_int,
        default=DEFAULT_LOOP_MAX_BACKOFF_SECONDS,
    )
    run_parser.add_argument(
        "--heartbeat",
        type=_positive_int,
        default=DEFAULT_LOOP_HEARTBEAT_SECONDS,
    )
    run_parser.add_argument("--max-runtime", type=_positive_int, default=None)

    status_parser = subparsers.add_parser(
        COMMAND_STATUS,
        parents=[common],
        help="Show a quick backlog snapshot",
    )

    stats_parser = subparsers.add_parser(
        COMMAND_STATS,
        parents=[common],
        help="Show aggregated backlog statistics",
    )

    health_parser = subparsers.add_parser(
        COMMAND_HEALTH,
        parents=[common],
        help="Show an operational health summary",
    )

    metrics_parser = subparsers.add_parser(
        COMMAND_METRICS,
        parents=[common],
        help="Show operational metrics",
    )
    metrics_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )

    parser.set_defaults(command=COMMAND_RUN)
    run_parser.set_defaults(command=COMMAND_RUN)
    status_parser.set_defaults(command=COMMAND_STATUS)
    stats_parser.set_defaults(command=COMMAND_STATS)
    health_parser.set_defaults(command=COMMAND_HEALTH)
    metrics_parser.set_defaults(command=COMMAND_METRICS)
    return parser


async def _open_session(
    session_factory: Callable[[], Awaitable[AsyncSession]] | None,
) -> AsyncSession:
    factory = session_factory or get_db_session
    return await factory()


async def _close_session(session: Any) -> None:
    close = getattr(session, "close", None)
    if callable(close):
        await close()


async def _collect_backlog_snapshot(
    session_factory: Callable[[], Awaitable[AsyncSession]] | None,
    *,
    tenant_id: UUID | None,
    event_type: str | None,
) -> Any:
    """Collect a safe backlog snapshot through a managed session."""

    session = await _open_session(session_factory)
    try:
        return await collect_outbox_backlog_snapshot(
            session,
            tenant_id=tenant_id,
            event_type=event_type,
        )
    finally:
        await _close_session(session)


def _install_signal_handlers(
    loop: asyncio.AbstractEventLoop,
    stop_event: asyncio.Event,
) -> list[signal.Signals]:
    """Install graceful shutdown handlers for SIGINT and SIGTERM."""

    handlers: list[signal.Signals] = []
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
            handlers.append(sig)
        except NotImplementedError:
            continue
    return handlers


def _remove_signal_handlers(
    loop: asyncio.AbstractEventLoop,
    handlers: list[signal.Signals],
) -> None:
    """Remove previously installed signal handlers."""

    for sig in handlers:
        try:
            loop.remove_signal_handler(sig)
        except NotImplementedError:
            continue


def _worker_logger(
    *,
    worker_run_id: UUID,
    command: str,
    batch_size: int | None = None,
    max_batches: int | None = None,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
    locked_by: str | None = None,
    verbose: bool = False,
) -> Any:
    return logger.bind(
        component="domain_event_outbox_worker",
        worker_run_id=str(worker_run_id),
        command=command,
        batch_size=batch_size,
        max_batches=max_batches,
        tenant_id=str(tenant_id) if tenant_id else None,
        event_type=event_type,
        locked_by=locked_by,
        verbose=verbose,
    )


async def run_outbox_relay_once(
    batch_size: int = 50,
    locked_by: str | None = None,
    max_batches: int = 1,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
    stop_on_error: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    session_factory: Callable[[], Awaitable[AsyncSession]] | None = None,
) -> OutboxWorkerRunResult:
    """Run the outbox relay in bounded batches and consolidate the results."""

    worker_run_id = uuid4()
    started_at = datetime.now(UTC)
    start = perf_counter()
    result = OutboxWorkerRunResult(
        worker_run_id=worker_run_id,
        dry_run=dry_run,
        started_at=started_at,
    )
    bound_logger = _worker_logger(
        worker_run_id=worker_run_id,
        command=COMMAND_RUN,
        batch_size=batch_size,
        max_batches=max_batches,
        tenant_id=tenant_id,
        event_type=event_type,
        locked_by=locked_by,
        verbose=verbose,
    )
    bound_logger.info("domain_event_outbox_worker_started")

    session = await _open_session(session_factory)
    try:
        service = DomainEventOutboxService(session=session)
        if dry_run:
            candidates = await service.list_pending(
                batch_size=batch_size,
                tenant_id=tenant_id,
                event_type=event_type,
            )
            result.status = "dry_run"
            result.exit_code = EXIT_OK
            result.total_batches = 1 if candidates else 0
            result.total_claimed = len(candidates)
            result.warnings.append("dry_run")
            if verbose:
                for candidate in candidates:
                    result.batch_runs.append(
                        {
                            "batch": 1,
                            "outbox_id": str(candidate.id),
                            "event_type": candidate.event_type,
                            "tenant_id": str(candidate.tenant_id),
                        }
                    )
            _log_run_summary(bound_logger, result)
            return result

        relay = DomainEventOutboxRelay(session=session)
        initial_pending = await service.list_pending(
            batch_size=batch_size,
            tenant_id=tenant_id,
            event_type=event_type,
        )
        while result.total_batches < max_batches:
            batch_started = perf_counter()
            try:
                relay_result = await relay.run_once(
                    batch_size=batch_size,
                    tenant_id=tenant_id,
                    relay_id=locked_by,
                    event_type=event_type,
                )
            except KeyboardInterrupt:
                result.status = "interrupted"
                result.warnings.append("keyboard_interrupt")
                result.exit_code = EXIT_INTERRUPTED
                raise
            except Exception as exc:  # pragma: no cover - defensive isolation
                error = f"{exc.__class__.__name__}: {exc}"
                result.errors.append(error)
                result.exit_code = EXIT_OPERATIONAL_ERROR
                if stop_on_error:
                    break
                result.status = "failed"
                break

            result.relay_runs.append(relay_result)
            result.total_batches += 1
            result.total_claimed += relay_result.total_claimed
            result.total_processed += relay_result.processed
            result.total_failed += relay_result.failed
            result.total_dead_letter += relay_result.dead_letter
            batch_duration_ms = int((perf_counter() - batch_started) * 1000)
            result.batch_runs.append(
                {
                    "batch": result.total_batches,
                    "claimed": relay_result.total_claimed,
                    "processed": relay_result.processed,
                    "failed": relay_result.failed,
                    "dead_letter": relay_result.dead_letter,
                    "duration_ms": batch_duration_ms,
                }
            )
            if verbose:
                bound_logger.bind(
                    batch=result.total_batches,
                    claimed=relay_result.total_claimed,
                    processed=relay_result.processed,
                    failed=relay_result.failed,
                    dead_letter=relay_result.dead_letter,
                    duration_ms=batch_duration_ms,
                ).info("domain_event_outbox_worker_batch_finished")
            if relay_result.total_claimed == 0:
                result.warnings.append("no_pending_rows")
                if initial_pending:
                    result.status = "lock_not_obtained"
                    result.exit_code = EXIT_LOCK_NOT_OBTAINED
                break

        if result.exit_code == EXIT_OK and result.errors:
            result.exit_code = EXIT_OPERATIONAL_ERROR
        if result.exit_code == EXIT_OK and result.total_batches > 0:
            result.status = "completed"
        if result.exit_code == EXIT_OK and not result.total_batches:
            result.status = "completed"
    finally:
        if session:
            await _close_session(session)
        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(UTC)
        if result.exit_code == EXIT_OK and result.errors:
            result.exit_code = EXIT_OPERATIONAL_ERROR
        _log_run_summary(bound_logger, result)
    return result


async def run_outbox_worker_loop(
    *,
    batch_size: int = 50,
    locked_by: str | None = None,
    max_batches: int = 1,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
    stop_on_error: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    interval: int = DEFAULT_LOOP_INTERVAL_SECONDS,
    backoff: int = DEFAULT_LOOP_BACKOFF_SECONDS,
    max_backoff: int = DEFAULT_LOOP_MAX_BACKOFF_SECONDS,
    heartbeat: int = DEFAULT_LOOP_HEARTBEAT_SECONDS,
    max_runtime: int | None = None,
    session_factory: Callable[[], Awaitable[AsyncSession]] | None = None,
) -> OutboxWorkerRunResult:
    """Run the outbox relay continuously until stopped or max-runtime is reached."""

    worker_run_id = uuid4()
    started_at = datetime.now(UTC)
    stats = WorkerStats(started_at=started_at)
    metrics = reset_observability_metrics(started_at)
    result = OutboxWorkerRunResult(
        worker_run_id=worker_run_id,
        dry_run=dry_run,
        started_at=started_at,
    )
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    handlers = _install_signal_handlers(loop, stop_event)
    bound_logger = _worker_logger(
        worker_run_id=worker_run_id,
        command=COMMAND_RUN,
        batch_size=batch_size,
        max_batches=max_batches,
        tenant_id=tenant_id,
        event_type=event_type,
        locked_by=locked_by,
        verbose=verbose,
    )
    current_backoff = backoff
    result.status = "running"
    bound_logger.info("worker starting")
    try:
        while not stop_event.is_set():
            if _max_runtime_reached(started_at, max_runtime):
                result.warnings.append("max_runtime_reached")
                break
            try:
                cycle_result = await run_outbox_relay_once(
                    batch_size=batch_size,
                    locked_by=locked_by,
                    max_batches=max_batches,
                    tenant_id=tenant_id,
                    event_type=event_type,
                    stop_on_error=stop_on_error,
                    dry_run=dry_run,
                    verbose=verbose,
                    session_factory=session_factory,
                )
            except Exception as exc:  # pragma: no cover - defensive isolation
                error = f"{exc.__class__.__name__}: {exc}"
                stats.mark_error(error)
                result.errors.append(error)
                result.status = "failed"
                result.exit_code = EXIT_OPERATIONAL_ERROR
                metrics.record_error(error, backlog=metrics.current_backlog)
                _log_cycle_failure(bound_logger, stats, error, current_backoff)
                if stop_on_error:
                    break
                await _sleep_with_timeout(
                    current_backoff,
                    started_at,
                    max_runtime,
                    stop_event,
                )
                current_backoff = _increase_backoff(current_backoff, max_backoff)
                continue

            _accumulate_cycle(result, cycle_result)
            if cycle_result.exit_code in (EXIT_OK, EXIT_LOCK_NOT_OBTAINED):
                stats.mark_cycle(cycle_result)
                metrics.record_cycle(
                    batches=cycle_result.total_batches,
                    batch_size=cycle_result.total_claimed,
                    processed=cycle_result.total_processed,
                    failed=cycle_result.total_failed,
                    backlog=metrics.current_backlog,
                )
                current_backoff = backoff
                _log_cycle_summary(bound_logger, cycle_result, stats)
            else:
                stats.mark_error(
                    cycle_result.errors[0]
                    if cycle_result.errors
                    else f"cycle_exit_code={cycle_result.exit_code}"
                )
                error = cycle_result.errors[0] if cycle_result.errors else (
                    f"cycle_exit_code={cycle_result.exit_code}"
                )
                metrics.record_error(error, backlog=metrics.current_backlog)
                _log_cycle_failure(bound_logger, stats, error, current_backoff)
                if stop_on_error:
                    break
                await _sleep_with_timeout(
                    current_backoff,
                    started_at,
                    max_runtime,
                    stop_event,
                )
                current_backoff = _increase_backoff(current_backoff, max_backoff)
                result.exit_code = cycle_result.exit_code
                result.status = cycle_result.status
                continue
            if stop_event.is_set():
                break
            if _should_emit_heartbeat(stats, heartbeat):
                try:
                    snapshot = await _collect_backlog_snapshot(
                        session_factory,
                        tenant_id=tenant_id,
                        event_type=event_type,
                    )
                except Exception as exc:  # pragma: no cover - defensive isolation
                    bound_logger.bind(
                        exception_type=exc.__class__.__name__,
                        exception_message=str(exc),
                    ).warning("worker heartbeat snapshot_failed")
                else:
                    metrics.apply_snapshot(snapshot)
                _log_heartbeat(bound_logger, stats, metrics)
            if _max_runtime_reached(started_at, max_runtime):
                result.warnings.append("max_runtime_reached")
                break
            await _sleep_with_timeout(
                interval,
                started_at,
                max_runtime,
                stop_event,
            )
    finally:
        _remove_signal_handlers(loop, handlers)
    result.finished_at = datetime.now(UTC)
    result.duration_ms = int((result.finished_at - started_at).total_seconds() * 1000)
    if stop_event.is_set():
        result.status = "interrupted"
        result.exit_code = EXIT_INTERRUPTED
        result.warnings.append("signal_received")
    elif _max_runtime_reached(started_at, max_runtime):
        result.status = "stopped"
        result.exit_code = EXIT_OK
    elif result.exit_code == EXIT_OK:
        result.status = "completed"
    bound_logger.bind(
        status=result.status,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        cycles=stats.cycles,
        batches_processed=stats.batches_processed,
        events_processed=stats.events_processed,
        errors=stats.errors,
        last_success=stats.last_success.isoformat() if stats.last_success else None,
        last_error=stats.last_error,
    ).info("worker stopped gracefully")
    return result


async def collect_outbox_status(
    *,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
    session_factory: Callable[[], Awaitable[AsyncSession]] | None = None,
) -> OutboxWorkerStatusResult:
    """Return a quick snapshot of outbox backlog by status."""

    worker_run_id = uuid4()
    session = await _open_session(session_factory)
    try:
        counts = await _query_status_counts(session, tenant_id=tenant_id, event_type=event_type)
        total = sum(counts.values())
        result = OutboxWorkerStatusResult(
            worker_run_id=worker_run_id,
            tenant_id=tenant_id,
            event_type=event_type,
            pending=counts["pending"],
            processing=counts["processing"],
            failed=counts["failed"],
            dead_letter=counts["dead_letter"],
            processed=counts["processed"],
            total=total,
            backlog_estimated=counts["pending"] + counts["processing"] + counts["failed"],
        )
        logger.bind(
            component="domain_event_outbox_worker",
            worker_run_id=str(worker_run_id),
            command=COMMAND_STATUS,
            tenant_id=str(tenant_id) if tenant_id else None,
            event_type=event_type,
            pending=result.pending,
            processing=result.processing,
            failed=result.failed,
            dead_letter=result.dead_letter,
            processed=result.processed,
            backlog_estimated=result.backlog_estimated,
        ).info("domain_event_outbox_worker_status")
        return result
    finally:
        await _close_session(session)


async def collect_outbox_stats(
    *,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
    session_factory: Callable[[], Awaitable[AsyncSession]] | None = None,
) -> OutboxWorkerStatsResult:
    """Return aggregated outbox statistics."""

    worker_run_id = uuid4()
    session = await _open_session(session_factory)
    try:
        by_status = await _query_status_counts(session, tenant_id=tenant_id, event_type=event_type)
        by_event_type = await _query_event_type_counts(
            session,
            tenant_id=tenant_id,
            event_type=event_type,
        )
        by_tenant = await _query_tenant_counts(
            session,
            tenant_id=tenant_id,
            event_type=event_type,
        )
        total = sum(by_status.values())
        result = OutboxWorkerStatsResult(
            worker_run_id=worker_run_id,
            tenant_id=tenant_id,
            event_type=event_type,
            total=total,
            backlog_estimated=by_status["pending"] + by_status["processing"] + by_status["failed"],
            by_status=by_status,
            by_event_type=by_event_type,
            by_tenant=by_tenant,
        )
        logger.bind(
            component="domain_event_outbox_worker",
            worker_run_id=str(worker_run_id),
            command=COMMAND_STATS,
            tenant_id=str(tenant_id) if tenant_id else None,
            event_type=event_type,
            total=result.total,
            backlog_estimated=result.backlog_estimated,
        ).info("domain_event_outbox_worker_stats")
        return result
    finally:
        await _close_session(session)


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


def _log_run_summary(logger_ctx: Any, result: OutboxWorkerRunResult) -> None:
    logger_ctx.bind(
        status=result.status,
        exit_code=result.exit_code,
        start_time=result.started_at.isoformat() if result.started_at else None,
        finish_time=result.finished_at.isoformat() if result.finished_at else None,
        duration_ms=result.duration_ms,
        total_batches=result.total_batches,
        claimed=result.total_claimed,
        processed=result.total_processed,
        failed=result.total_failed,
        dead_letter=result.total_dead_letter,
        skipped=max(result.total_claimed - result.total_processed - result.total_failed, 0),
        warnings=len(result.warnings),
        verbose=bool(result.batch_runs),
    ).info("domain_event_outbox_worker_summary")


def _accumulate_cycle(
    worker_result: OutboxWorkerRunResult,
    cycle_result: OutboxWorkerRunResult,
) -> None:
    """Merge a cycle result into the continuous worker summary."""

    worker_result.relay_runs.extend(cycle_result.relay_runs)
    worker_result.batch_runs.extend(cycle_result.batch_runs)
    worker_result.errors.extend(cycle_result.errors)
    worker_result.warnings.extend(cycle_result.warnings)
    worker_result.total_batches += cycle_result.total_batches
    worker_result.total_claimed += cycle_result.total_claimed
    worker_result.total_processed += cycle_result.total_processed
    worker_result.total_failed += cycle_result.total_failed
    worker_result.total_dead_letter += cycle_result.total_dead_letter
    if cycle_result.exit_code not in (EXIT_OK, EXIT_LOCK_NOT_OBTAINED):
        worker_result.exit_code = cycle_result.exit_code
        worker_result.status = cycle_result.status


def _increase_backoff(current_backoff: int, max_backoff: int) -> int:
    """Increase the retry backoff with an upper bound."""

    return min(current_backoff * 2, max_backoff)


def _should_emit_heartbeat(stats: WorkerStats, heartbeat_seconds: int) -> bool:
    """Return whether the worker heartbeat should be logged now."""

    if stats.last_heartbeat_at is None:
        return True
    elapsed = (datetime.now(UTC) - stats.last_heartbeat_at).total_seconds()
    return elapsed >= heartbeat_seconds


def _log_heartbeat(
    logger_ctx: Any,
    stats: WorkerStats,
    metrics: OutboxMetrics,
) -> None:
    """Log a structured worker heartbeat."""

    stats.last_heartbeat_at = datetime.now(UTC)
    logger_ctx.bind(
        **metrics.to_dict(),
    ).info("worker alive")


def _log_cycle_summary(
    logger_ctx: Any,
    cycle_result: OutboxWorkerRunResult,
    stats: WorkerStats,
) -> None:
    """Log a structured summary for one worker cycle."""

    logger_ctx.bind(
        cycle_status=cycle_result.status,
        cycle_exit_code=cycle_result.exit_code,
        batches=cycle_result.total_batches,
        claimed=cycle_result.total_claimed,
        processed=cycle_result.total_processed,
        failed=cycle_result.total_failed,
        dead_letter=cycle_result.total_dead_letter,
        uptime=stats.uptime,
        cycles=stats.cycles,
    ).info("batch processed")


def _log_cycle_failure(
    logger_ctx: Any,
    stats: WorkerStats,
    error: str,
    retry_in: int,
) -> None:
    """Log a structured failure with the next retry delay."""

    logger_ctx.bind(
        retries_in=retry_in,
        uptime=stats.uptime,
        cycles=stats.cycles,
        errors=stats.errors,
        last_error=error,
    ).error("processing failed")


def _max_runtime_reached(started_at: datetime, max_runtime: int | None) -> bool:
    """Return whether the configured runtime limit has been reached."""

    if max_runtime is None:
        return False
    return (datetime.now(UTC) - started_at) >= timedelta(seconds=max_runtime)


async def _sleep_with_timeout(
    seconds: int,
    started_at: datetime,
    max_runtime: int | None,
    stop_event: asyncio.Event,
) -> None:
    """Sleep without exceeding the configured max runtime."""

    if stop_event.is_set():
        return
    delay = seconds
    if max_runtime is not None:
        remaining = max_runtime - int((datetime.now(UTC) - started_at).total_seconds())
        if remaining <= 0:
            return
        delay = min(delay, remaining)
    await asyncio.sleep(delay)


async def _async_main(args: argparse.Namespace) -> int:
    command = getattr(args, "command", COMMAND_RUN)
    if command == COMMAND_RUN:
        if getattr(args, "loop", False):
            result = await run_outbox_worker_loop(
                batch_size=args.batch_size,
                locked_by=args.locked_by,
                max_batches=args.max_batches,
                tenant_id=UUID(args.tenant_id) if args.tenant_id else None,
                event_type=args.event_type,
                stop_on_error=args.stop_on_error,
                dry_run=args.dry_run,
                verbose=args.verbose,
                interval=args.interval,
                backoff=args.backoff,
                max_backoff=args.max_backoff,
                heartbeat=args.heartbeat,
                max_runtime=args.max_runtime,
            )
            return result.exit_code
        result = await run_outbox_relay_once(
            batch_size=args.batch_size,
            locked_by=args.locked_by,
            max_batches=args.max_batches,
            tenant_id=UUID(args.tenant_id) if args.tenant_id else None,
            event_type=args.event_type,
            stop_on_error=args.stop_on_error,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        return result.exit_code
    if command == COMMAND_STATUS:
        result = await collect_outbox_status(
            tenant_id=UUID(args.tenant_id) if args.tenant_id else None,
            event_type=args.event_type,
        )
        return result.exit_code
    if command == COMMAND_STATS:
        result = await collect_outbox_stats(
            tenant_id=UUID(args.tenant_id) if args.tenant_id else None,
            event_type=args.event_type,
        )
        return result.exit_code
    if command == COMMAND_HEALTH:
        session = await _open_session(None)
        try:
            report = await collect_outbox_health(
                session,
                tenant_id=UUID(args.tenant_id) if args.tenant_id else None,
                event_type=args.event_type,
                base_metrics=get_observability_metrics(),
            )
        finally:
            await _close_session(session)
        print(render_outbox_health_text(report))
        return EXIT_OK
    if command == COMMAND_METRICS:
        session = await _open_session(None)
        try:
            metrics = await collect_outbox_metrics(
                session,
                tenant_id=UUID(args.tenant_id) if args.tenant_id else None,
                event_type=args.event_type,
                base_metrics=get_observability_metrics(),
            )
        finally:
            await _close_session(session)
        rendered = (
            render_outbox_metrics_json(metrics)
            if getattr(args, "format", "text") == "json"
            else render_outbox_metrics_text(metrics)
        )
        print(rendered)
        return EXIT_OK
    raise ValueError(f"Unsupported command: {command}")


def _run_with_event_loop(args: argparse.Namespace) -> int:
    """Run the async entrypoint on a dedicated event loop."""

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_async_main(args))
    except KeyboardInterrupt:
        logger.bind(component="domain_event_outbox_worker").info(
            "domain_event_outbox_worker_interrupted"
        )
        return EXIT_INTERRUPTED
    finally:
        try:
            loop.run_until_complete(engine.dispose())
        finally:
            asyncio.set_event_loop(None)
            loop.close()


def main(argv: list[str] | None = None) -> int:
    """Run the internal worker entrypoint."""

    parser = build_parser()
    normalized_argv = _normalize_argv(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(normalized_argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else EXIT_CONFIG_ERROR

    try:
        if getattr(args, "loop", False) and getattr(args, "command", COMMAND_RUN) == COMMAND_RUN:
            return _run_with_event_loop(args)
        return asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        logger.bind(component="domain_event_outbox_worker").info(
            "domain_event_outbox_worker_interrupted"
        )
        return EXIT_INTERRUPTED
    except ValueError as exc:
        logger.bind(component="domain_event_outbox_worker", error=str(exc)).error(
            "domain_event_outbox_worker_configuration_error"
        )
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # pragma: no cover - defensive isolation
        logger.bind(
            component="domain_event_outbox_worker",
            exception_type=exc.__class__.__name__,
            exception_message=str(exc),
        ).exception("domain_event_outbox_worker_unexpected_error")
        return EXIT_UNEXPECTED_ERROR
    finally:
        try:
            asyncio.run(engine.dispose())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(engine.dispose())
            finally:
                loop.close()


if __name__ == "__main__":
    raise SystemExit(main())
