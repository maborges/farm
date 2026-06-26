from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import engine, get_db_session

from .outbox_model import DomainEventOutbox
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
COMMANDS = (COMMAND_RUN, COMMAND_STATUS, COMMAND_STATS)


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
            "Commands: run, status, stats. "
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

    parser.set_defaults(command=COMMAND_RUN)
    run_parser.set_defaults(command=COMMAND_RUN)
    status_parser.set_defaults(command=COMMAND_STATUS)
    stats_parser.set_defaults(command=COMMAND_STATS)
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
        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(UTC)
        if result.exit_code == EXIT_OK and result.errors:
            result.exit_code = EXIT_OPERATIONAL_ERROR
        _log_run_summary(bound_logger, result)
        await _close_session(session)
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


async def _async_main(args: argparse.Namespace) -> int:
    command = getattr(args, "command", COMMAND_RUN)
    if command == COMMAND_RUN:
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
    raise ValueError(f"Unsupported command: {command}")


def main(argv: list[str] | None = None) -> int:
    """Run the internal worker entrypoint."""

    parser = build_parser()
    normalized_argv = _normalize_argv(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(normalized_argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else EXIT_CONFIG_ERROR

    try:
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
