from __future__ import annotations

import uuid
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


@pytest.mark.asyncio
async def test_run_outbox_relay_once_processes_bounded_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    relay = _FakeRelay(session)

    async def session_factory() -> _FakeSession:
        return session

    monkeypatch.setattr(outbox_worker_module, "DomainEventOutboxRelay", lambda session: relay)

    result = await outbox_worker_module.run_outbox_relay_once(
        batch_size=25,
        max_batches=2,
        session_factory=session_factory,
    )

    assert result.total_batches == 2
    assert result.total_claimed == 3
    assert result.total_processed == 3
    assert result.total_failed == 0
    assert result.total_dead_letter == 0
    assert session.closed is True


@pytest.mark.asyncio
async def test_run_outbox_relay_once_propagates_filters_and_locked_by(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    relay = _FakeRelay(session)

    async def session_factory() -> _FakeSession:
        return session

    monkeypatch.setattr(outbox_worker_module, "DomainEventOutboxRelay", lambda session: relay)
    tenant_id = uuid.uuid4()

    result = await outbox_worker_module.run_outbox_relay_once(
        batch_size=10,
        max_batches=1,
        locked_by="worker-a",
        tenant_id=tenant_id,
        event_type="campo.sync.falha",
        session_factory=session_factory,
    )

    assert result.total_batches == 1
    assert relay.calls[0]["batch_size"] == 10
    assert relay.calls[0]["tenant_id"] == tenant_id
    assert relay.calls[0]["relay_id"] == "worker-a"
    assert relay.calls[0]["event_type"] == "campo.sync.falha"


@pytest.mark.asyncio
async def test_run_outbox_relay_once_collects_error_without_stopping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()

    class FailingRelay:
        def __init__(self, session: object) -> None:  # noqa: D401, ARG002
            self.calls = 0

        async def run_once(self, *args: object, **kwargs: object) -> DomainEventOutboxRelayResult:  # noqa: ANN002, ANN003
            self.calls += 1
            raise RuntimeError("relay boom")

    async def session_factory() -> _FakeSession:
        return session

    monkeypatch.setattr(outbox_worker_module, "DomainEventOutboxRelay", FailingRelay)

    result = await outbox_worker_module.run_outbox_relay_once(
        session_factory=session_factory,
    )

    assert result.total_batches == 0
    assert result.errors == ["RuntimeError: relay boom"]
    assert session.closed is True


def test_main_invokes_async_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def async_main(args: object) -> SimpleNamespace:
        captured["args"] = args
        return SimpleNamespace()

    async def dispose() -> None:
        return None

    monkeypatch.setattr(outbox_worker_module, "_async_main", async_main)
    monkeypatch.setattr(
        outbox_worker_module,
        "engine",
        SimpleNamespace(dispose=dispose),
    )

    exit_code = outbox_worker_module.main(
        [
            "--batch-size",
            "3",
            "--max-batches",
            "2",
            "--locked-by",
            "worker-cli",
            "--tenant-id",
            str(uuid.uuid4()),
            "--event-type",
            "campo.tarefa.invalidada",
            "--stop-on-error",
        ]
    )

    assert exit_code == 0
    args = cast(SimpleNamespace, captured["args"])
    assert args.batch_size == 3
    assert args.max_batches == 2
    assert args.locked_by == "worker-cli"
    assert args.event_type == "campo.tarefa.invalidada"
    assert args.stop_on_error is True
