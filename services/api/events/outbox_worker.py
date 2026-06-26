from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import engine, get_db_session

from .outbox_relay import DomainEventOutboxRelay, DomainEventOutboxRelayResult


class OutboxWorkerRunResult(BaseModel):  # type: ignore[misc]
    """Canonical summary for an outbox worker execution."""

    worker_run_id: UUID
    total_batches: int = 0
    total_claimed: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_dead_letter: int = 0
    duration_ms: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    relay_runs: list[DomainEventOutboxRelayResult] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


async def run_outbox_relay_once(
    batch_size: int = 50,
    locked_by: str | None = None,
    max_batches: int = 1,
    tenant_id: UUID | None = None,
    event_type: str | None = None,
    stop_on_error: bool = False,
    session_factory: Callable[[], Awaitable[AsyncSession]] | None = None,
) -> OutboxWorkerRunResult:
    """Run the outbox relay in bounded batches and consolidate the results."""

    worker_run_id = uuid4()
    started_at = datetime.now(timezone.utc)  # noqa: UP017
    start = perf_counter()
    bound_logger = logger.bind(
        component="domain_event_outbox_worker",
        worker_run_id=str(worker_run_id),
        locked_by=locked_by,
        batch_size=batch_size,
        max_batches=max_batches,
        tenant_id=str(tenant_id) if tenant_id else None,
        event_type=event_type,
    )
    bound_logger.info("domain_event_outbox_worker_started")

    session = await (session_factory or get_db_session)()
    try:
        relay = DomainEventOutboxRelay(session=session)
        result = OutboxWorkerRunResult(worker_run_id=worker_run_id)
        while result.total_batches < max_batches:
            try:
                relay_result = await relay.run_once(
                    batch_size=batch_size,
                    tenant_id=tenant_id,
                    relay_id=locked_by,
                    event_type=event_type,
                )
            except Exception as exc:  # pragma: no cover - defensive isolation
                error = f"{exc.__class__.__name__}: {exc}"
                result.errors.append(error)
                if stop_on_error:
                    raise
                break
            result.relay_runs.append(relay_result)
            result.total_batches += 1
            result.total_claimed += relay_result.total_claimed
            result.total_processed += relay_result.processed
            result.total_failed += relay_result.failed
            result.total_dead_letter += relay_result.dead_letter
            if relay_result.total_claimed == 0:
                result.warnings.append("no_pending_rows")
                break
        result.duration_ms = int((perf_counter() - start) * 1000)
        bound_logger.bind(
            claimed=result.total_claimed,
            processed=result.total_processed,
            failed=result.total_failed,
            dead_letter=result.total_dead_letter,
            duration_ms=result.duration_ms,
            status="completed",
        ).info("domain_event_outbox_worker_finished")
        return result
    except Exception as exc:  # pragma: no cover - defensive isolation
        error = f"{exc.__class__.__name__}: {exc}"
        bound_logger.bind(
            status="failed",
            error=error,
            duration_ms=int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),  # noqa: UP017
        ).exception("domain_event_outbox_worker_failed")
        raise
    finally:
        close = getattr(session, "close", None)
        if callable(close):
            await close()


async def _async_main(args: argparse.Namespace) -> OutboxWorkerRunResult:
    return await run_outbox_relay_once(
        batch_size=args.batch_size,
        locked_by=args.locked_by,
        max_batches=args.max_batches,
        tenant_id=UUID(args.tenant_id) if args.tenant_id else None,
        event_type=args.event_type,
        stop_on_error=args.stop_on_error,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the internal worker CLI parser."""

    parser = argparse.ArgumentParser(description="Run the domain-event outbox relay")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-batches", type=int, default=1)
    parser.add_argument("--locked-by", type=str, default=None)
    parser.add_argument("--tenant-id", type=str, default=None)
    parser.add_argument("--event-type", type=str, default=None)
    parser.add_argument("--stop-on-error", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the internal worker entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        logger.info("domain_event_outbox_worker_interrupted")
        return 130
    finally:
        asyncio.run(engine.dispose())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
