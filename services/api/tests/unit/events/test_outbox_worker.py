from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
from datetime import datetime
from types import SimpleNamespace
from typing import cast

import pytest

import events.outbox_worker as outbox_worker_module
from events import DomainEventOutboxRelayResult


class _FakeSession:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakeRelay:
    def __init__(self, session: object) -> None:  # noqa: D401, ARG002
        self.session = session
        self.calls: list[dict[str, object]] = []

    async def run_once(
        self,
        batch_size: int = 50,
        tenant_id: uuid.UUID | None = None,
        relay_id: uuid.UUID | str | None = None,
        event_type: str | None = None,
    ) -> DomainEventOutboxRelayResult:
        self.calls.append(
            {
                "batch_size": batch_size,
                "tenant_id": tenant_id,
                "relay_id": relay_id,
                "event_type": event_type,
            }
        )
        claimed = len(self.calls)
        return DomainEventOutboxRelayResult(
            relay_id=uuid.uuid4(),
            total_claimed=claimed,
            processed=claimed,
            failed=0,
            dead_letter=0,
            duration_ms=1,
        )


class _FakeService:
    def __init__(self, rows: Sequence[object]) -> None:
        self.rows = rows
        self.list_pending_calls: list[dict[str, object | None]] = []

    async def list_pending(
        self,
        batch_size: int = 50,
        tenant_id: uuid.UUID | None = None,
        event_type: str | None = None,
    ) -> list[object]:
        self.list_pending_calls.append(
            {
                "batch_size": batch_size,
                "tenant_id": tenant_id,
                "event_type": event_type,
            }
        )
        return list(self.rows)


@pytest.mark.parametrize(
    ("argv", "expected_command"),
    [
        (["run"], "run"),
        (["status"], "status"),
        (["stats"], "stats"),
    ],
)
def test_parser_exposes_commands_and_options(argv: list[str], expected_command: str) -> None:
    parser = outbox_worker_module.build_parser()
    parsed = parser.parse_args(argv)

    assert parsed.command == expected_command


def test_parser_defaults_to_run_for_plain_flags() -> None:
    parser = outbox_worker_module.build_parser()
    parsed = parser.parse_args(outbox_worker_module._normalize_argv(["--verbose"]))

    assert parsed.command == "run"
    assert parsed.verbose is True


@pytest.mark.asyncio
async def test_run_command_processes_bounded_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    relay = _FakeRelay(session)
    fake_service = _FakeService(
        [
            SimpleNamespace(
                id=uuid.uuid4(),
                event_type="campo.sync.falha",
                tenant_id=uuid.uuid4(),
            ),
            SimpleNamespace(
                id=uuid.uuid4(),
                event_type="campo.sync.falha",
                tenant_id=uuid.uuid4(),
            ),
        ]
    )

    async def session_factory() -> _FakeSession:
        return session

    monkeypatch.setattr(outbox_worker_module, "DomainEventOutboxRelay", lambda session: relay)
    monkeypatch.setattr(
        outbox_worker_module,
        "DomainEventOutboxService",
        lambda session: fake_service,
    )

    result = await outbox_worker_module.run_outbox_relay_once(
        batch_size=25,
        max_batches=2,
        session_factory=session_factory,
    )

    assert result.exit_code == outbox_worker_module.EXIT_OK
    assert result.total_batches == 2
    assert result.total_claimed == 3
    assert result.total_processed == 3
    assert session.closed is True


@pytest.mark.asyncio
async def test_dry_run_lists_candidates_without_relay_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    fake_rows = [
        SimpleNamespace(
            id=uuid.uuid4(),
            event_type="campo.sync.falha",
            tenant_id=uuid.uuid4(),
        )
    ]
    fake_service = _FakeService(fake_rows)

    async def session_factory() -> _FakeSession:
        return session

    monkeypatch.setattr(
        outbox_worker_module,
        "DomainEventOutboxService",
        lambda session: fake_service,
    )

    result = await outbox_worker_module.run_outbox_relay_once(
        batch_size=10,
        dry_run=True,
        verbose=True,
        session_factory=session_factory,
    )

    assert result.dry_run is True
    assert result.exit_code == outbox_worker_module.EXIT_OK
    assert result.total_claimed == 1
    assert result.warnings == ["dry_run"]
    assert result.batch_runs
    assert fake_service.list_pending_calls[0]["batch_size"] == 10


@pytest.mark.asyncio
async def test_run_command_returns_lock_not_obtained_when_pending_exists_but_nothing_claimed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    fake_service = _FakeService([SimpleNamespace(id=uuid.uuid4())])

    class LockedRelay:
        def __init__(self, session: object) -> None:  # noqa: D401, ARG002
            return None

        async def run_once(self, *args: object, **kwargs: object) -> DomainEventOutboxRelayResult:  # noqa: ANN002, ANN003
            return DomainEventOutboxRelayResult(
                relay_id=uuid.uuid4(),
                total_claimed=0,
                processed=0,
                failed=0,
                dead_letter=0,
                duration_ms=1,
            )

    async def session_factory() -> _FakeSession:
        return session

    monkeypatch.setattr(
        outbox_worker_module,
        "DomainEventOutboxService",
        lambda session: fake_service,
    )
    monkeypatch.setattr(outbox_worker_module, "DomainEventOutboxRelay", LockedRelay)

    result = await outbox_worker_module.run_outbox_relay_once(
        batch_size=5,
        session_factory=session_factory,
    )

    assert result.exit_code == outbox_worker_module.EXIT_LOCK_NOT_OBTAINED
    assert result.status == "lock_not_obtained"
    assert result.warnings == ["no_pending_rows"]


@pytest.mark.asyncio
async def test_verbose_mode_records_batch_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    relay = _FakeRelay(session)
    fake_service = _FakeService(
        [
            SimpleNamespace(
                id=uuid.uuid4(),
                event_type="campo.sync.falha",
                tenant_id=uuid.uuid4(),
            )
        ]
    )

    async def session_factory() -> _FakeSession:
        return session

    monkeypatch.setattr(outbox_worker_module, "DomainEventOutboxRelay", lambda session: relay)
    monkeypatch.setattr(
        outbox_worker_module,
        "DomainEventOutboxService",
        lambda session: fake_service,
    )

    result = await outbox_worker_module.run_outbox_relay_once(
        batch_size=10,
        max_batches=2,
        verbose=True,
        session_factory=session_factory,
    )

    assert len(result.batch_runs) == 2
    assert result.batch_runs[0]["batch"] == 1
    assert result.batch_runs[0]["claimed"] == 1


def test_invalid_batch_size_returns_config_error() -> None:
    exit_code = outbox_worker_module.main(["run", "--batch-size", "0"])

    assert exit_code == outbox_worker_module.EXIT_CONFIG_ERROR


def test_invalid_max_batches_returns_config_error() -> None:
    exit_code = outbox_worker_module.main(["run", "--max-batches", "0"])

    assert exit_code == outbox_worker_module.EXIT_CONFIG_ERROR


def test_help_returns_zero() -> None:
    exit_code = outbox_worker_module.main(["--help"])

    assert exit_code == outbox_worker_module.EXIT_OK


def test_status_command_returns_consolidated_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_status(**kwargs: object) -> SimpleNamespace:
        captured["kwargs"] = kwargs
        return SimpleNamespace(exit_code=0)

    monkeypatch.setattr(outbox_worker_module, "collect_outbox_status", fake_status)

    exit_code = outbox_worker_module.main(["status", "--tenant-id", str(uuid.uuid4())])

    assert exit_code == 0
    assert cast(dict[str, object], captured["kwargs"])["tenant_id"] is not None


def test_stats_command_returns_consolidated_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_stats(**kwargs: object) -> SimpleNamespace:
        captured["kwargs"] = kwargs
        return SimpleNamespace(exit_code=0)

    monkeypatch.setattr(outbox_worker_module, "collect_outbox_stats", fake_stats)

    exit_code = outbox_worker_module.main(["stats", "--event-type", "campo.sync.falha"])

    assert exit_code == 0
    assert cast(dict[str, object], captured["kwargs"])["event_type"] == "campo.sync.falha"


def test_keyboard_interrupt_returns_graceful_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(*args: object, **kwargs: object) -> None:  # noqa: ARG001
        raise KeyboardInterrupt

    monkeypatch.setattr(outbox_worker_module, "run_outbox_relay_once", boom)

    exit_code = outbox_worker_module.main(["run"])

    assert exit_code == outbox_worker_module.EXIT_INTERRUPTED


def test_main_invokes_run_handler_when_no_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_run(**kwargs: object) -> SimpleNamespace:
        captured["kwargs"] = kwargs
        return SimpleNamespace(exit_code=outbox_worker_module.EXIT_OK)

    monkeypatch.setattr(outbox_worker_module, "run_outbox_relay_once", fake_run)

    exit_code = outbox_worker_module.main(["--batch-size", "3", "--dry-run"])

    assert exit_code == 0
    assert cast(dict[str, object], captured["kwargs"])["batch_size"] == 3
    assert cast(dict[str, object], captured["kwargs"])["dry_run"] is True


def test_worker_stats_updates_runtime_counters() -> None:
    started_at = outbox_worker_module.datetime.now(outbox_worker_module.UTC)
    stats = outbox_worker_module.WorkerStats(started_at=started_at)
    cycle = outbox_worker_module.OutboxWorkerRunResult(
        worker_run_id=uuid.uuid4(),
        total_batches=2,
        total_processed=5,
    )

    stats.mark_cycle(cycle)
    stats.mark_error("boom")

    assert stats.cycles == 2
    assert stats.batches_processed == 2
    assert stats.events_processed == 5
    assert stats.errors == 1
    assert stats.last_success is not None
    assert stats.last_error == "boom"


@pytest.mark.asyncio
async def test_worker_loop_runs_multiple_cycles_and_respects_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[int] = []
    calls = 0

    async def fake_run_outbox_relay_once(
        **kwargs: object,
    ) -> outbox_worker_module.OutboxWorkerRunResult:
        nonlocal calls
        calls += 1
        return outbox_worker_module.OutboxWorkerRunResult(
            worker_run_id=uuid.uuid4(),
            total_batches=1,
            total_claimed=2,
            total_processed=2,
            total_failed=0,
            total_dead_letter=0,
        )

    runtime_checks = 0

    def fake_max_runtime_reached(started_at: datetime, max_runtime: int | None) -> bool:
        nonlocal runtime_checks
        runtime_checks += 1
        return runtime_checks >= 6

    async def fake_sleep(
        seconds: int,
        started_at: datetime,
        max_runtime: int | None,
        stop_event: asyncio.Event,
    ) -> None:
        sleeps.append(seconds)

    heartbeats: list[dict[str, object]] = []

    snapshot = SimpleNamespace(current_backlog=4, retries_seen=1)

    def fake_heartbeat(logger_ctx: object, stats: object, metrics: object) -> None:
        heartbeats.append(cast(dict[str, object], metrics.to_dict()))

    monkeypatch.setattr(outbox_worker_module, "run_outbox_relay_once", fake_run_outbox_relay_once)
    monkeypatch.setattr(outbox_worker_module, "_sleep_with_timeout", fake_sleep)
    monkeypatch.setattr(outbox_worker_module, "_log_heartbeat", fake_heartbeat)
    monkeypatch.setattr(outbox_worker_module, "_max_runtime_reached", fake_max_runtime_reached)
    async def fake_snapshot(*args: object, **kwargs: object) -> SimpleNamespace:  # noqa: ARG001
        return snapshot

    monkeypatch.setattr(outbox_worker_module, "_collect_backlog_snapshot", fake_snapshot)

    result = await outbox_worker_module.run_outbox_worker_loop(
        interval=7,
        heartbeat=0,
    )

    assert calls == 3
    assert sleeps == [7, 7]
    assert heartbeats
    assert heartbeats[0]["current_backlog"] == 4
    assert "throughput_per_minute" in heartbeats[0]
    assert result.exit_code == outbox_worker_module.EXIT_OK
    assert result.total_batches == 3
    assert result.total_processed == 6


@pytest.mark.asyncio
async def test_worker_loop_backoff_grows_and_resets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[int] = []
    calls = 0

    async def fake_run_outbox_relay_once(
        **kwargs: object,
    ) -> outbox_worker_module.OutboxWorkerRunResult:
        nonlocal calls
        calls += 1
        if calls == 1 or calls == 3:
            raise RuntimeError("boom")
        return outbox_worker_module.OutboxWorkerRunResult(
            worker_run_id=uuid.uuid4(),
            total_batches=1,
            total_claimed=1,
            total_processed=1,
            total_failed=0,
            total_dead_letter=0,
        )

    runtime_checks = 0

    def fake_max_runtime_reached(started_at: datetime, max_runtime: int | None) -> bool:
        nonlocal runtime_checks
        runtime_checks += 1
        return runtime_checks >= 5

    async def fake_sleep(
        seconds: int,
        started_at: datetime,
        max_runtime: int | None,
        stop_event: asyncio.Event,
    ) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(outbox_worker_module, "run_outbox_relay_once", fake_run_outbox_relay_once)
    monkeypatch.setattr(outbox_worker_module, "_sleep_with_timeout", fake_sleep)
    monkeypatch.setattr(outbox_worker_module, "_max_runtime_reached", fake_max_runtime_reached)
    async def fake_snapshot(*args: object, **kwargs: object) -> SimpleNamespace:  # noqa: ARG001
        return SimpleNamespace(current_backlog=2, retries_seen=5)

    monkeypatch.setattr(outbox_worker_module, "_collect_backlog_snapshot", fake_snapshot)

    result = await outbox_worker_module.run_outbox_worker_loop(
        interval=2,
        backoff=5,
        max_backoff=60,
    )

    assert sleeps == [5, 2, 5]
    assert result.errors[0] == "RuntimeError: boom"
    assert result.exit_code == outbox_worker_module.EXIT_OK
    assert result.status == "stopped"


def test_worker_loop_keyboard_interrupt_returns_130(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(**kwargs: object) -> outbox_worker_module.OutboxWorkerRunResult:
        raise KeyboardInterrupt

    monkeypatch.setattr(outbox_worker_module, "run_outbox_worker_loop", boom)

    exit_code = outbox_worker_module.main(["run", "--loop"])

    assert exit_code == outbox_worker_module.EXIT_INTERRUPTED


def test_worker_loop_sigterm_sets_graceful_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_install(loop: object, stop_event: asyncio.Event) -> list[object]:
        stop_event.set()
        return []

    async def fake_run_outbox_relay_once(
        **kwargs: object,
    ) -> outbox_worker_module.OutboxWorkerRunResult:
        return outbox_worker_module.OutboxWorkerRunResult(
            worker_run_id=uuid.uuid4(),
            total_batches=1,
            total_claimed=1,
            total_processed=1,
            total_failed=0,
            total_dead_letter=0,
        )

    monkeypatch.setattr(
        outbox_worker_module,
        "_install_signal_handlers",
        fake_install,
    )
    monkeypatch.setattr(
        outbox_worker_module,
        "run_outbox_relay_once",
        fake_run_outbox_relay_once,
    )

    exit_code = outbox_worker_module.main(["run", "--loop"])

    assert exit_code == outbox_worker_module.EXIT_INTERRUPTED


@pytest.mark.asyncio
async def test_worker_loop_stops_on_max_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    max_runtime_calls = 0

    async def fake_run_outbox_relay_once(
        **kwargs: object,
    ) -> outbox_worker_module.OutboxWorkerRunResult:
        return outbox_worker_module.OutboxWorkerRunResult(
            worker_run_id=uuid.uuid4(),
            total_batches=1,
            total_claimed=1,
            total_processed=1,
            total_failed=0,
            total_dead_letter=0,
        )

    def fake_max_runtime_reached(started_at: datetime, max_runtime: int | None) -> bool:
        nonlocal max_runtime_calls
        max_runtime_calls += 1
        return max_runtime_calls >= 2

    async def fake_sleep(
        seconds: int,
        started_at: datetime,
        max_runtime: int | None,
        stop_event: asyncio.Event,
    ) -> None:
        return None

    monkeypatch.setattr(outbox_worker_module, "run_outbox_relay_once", fake_run_outbox_relay_once)
    monkeypatch.setattr(outbox_worker_module, "_max_runtime_reached", fake_max_runtime_reached)
    monkeypatch.setattr(outbox_worker_module, "_sleep_with_timeout", fake_sleep)

    result = await outbox_worker_module.run_outbox_worker_loop(max_runtime=1)

    assert result.warnings == ["max_runtime_reached"]
    assert result.exit_code == outbox_worker_module.EXIT_OK
