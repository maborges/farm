from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

import pytest

import events.outbox_observability as observability_module
import events.outbox_worker as outbox_worker_module
from events import OutboxHealthStatus, OutboxMetrics


def test_metrics_initialize_and_compute_runtime() -> None:
    started_at = datetime.now(outbox_worker_module.UTC) - timedelta(seconds=60)
    metrics = OutboxMetrics(started_at=started_at)

    metrics.record_cycle(
        batches=2,
        batch_size=20,
        processed=8,
        failed=1,
        backlog=5,
        retries_seen=3,
    )

    data = metrics.to_dict()

    assert data["cycles"] == 1
    assert data["batches_processed"] == 2
    assert data["events_processed"] == 8
    assert data["current_backlog"] == 5
    assert data["average_batch_size"] == 10
    assert data["throughput_per_minute"] > 0
    assert data["uptime_seconds"] >= 60


def test_health_unknown_without_data() -> None:
    metrics = OutboxMetrics(started_at=datetime.now(outbox_worker_module.UTC))

    report = observability_module.evaluate_outbox_health(metrics)

    assert report.status == OutboxHealthStatus.UNKNOWN


def test_health_ok_with_low_backlog_and_recent_success() -> None:
    metrics = OutboxMetrics(started_at=datetime.now(outbox_worker_module.UTC))
    metrics.record_cycle(batches=1, batch_size=4, processed=4, backlog=1)

    report = observability_module.evaluate_outbox_health(metrics)

    assert report.status == OutboxHealthStatus.OK


def test_health_degraded_with_recent_error() -> None:
    metrics = OutboxMetrics(started_at=datetime.now(outbox_worker_module.UTC))
    metrics.record_error("boom")
    metrics.current_backlog = 3

    report = observability_module.evaluate_outbox_health(metrics)

    assert report.status == OutboxHealthStatus.DEGRADED


def test_health_critical_with_high_backlog() -> None:
    metrics = OutboxMetrics(started_at=datetime.now(outbox_worker_module.UTC))
    metrics.current_backlog = 500

    report = observability_module.evaluate_outbox_health(metrics)

    assert report.status == OutboxHealthStatus.CRITICAL


@pytest.mark.asyncio
async def test_snapshot_is_safe_and_filters_are_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object | None] = {}

    async def fake_status(session: object, *, tenant_id=None, event_type=None):  # noqa: ANN001
        captured["tenant_id"] = tenant_id
        captured["event_type"] = event_type
        return {"pending": 1, "processing": 0, "failed": 2, "dead_letter": 0, "processed": 7}

    async def fake_event_types(session: object, *, tenant_id=None, event_type=None):  # noqa: ANN001
        return {"campo.sync.falha": 3}

    async def fake_tenants(session: object, *, tenant_id=None, event_type=None):  # noqa: ANN001
        return {"tenant-a": 3}

    async def fake_retries(session: object, *, tenant_id=None, event_type=None):  # noqa: ANN001
        return 4

    monkeypatch.setattr(observability_module, "_query_status_counts", fake_status)
    monkeypatch.setattr(observability_module, "_query_event_type_counts", fake_event_types)
    monkeypatch.setattr(observability_module, "_query_tenant_counts", fake_tenants)
    monkeypatch.setattr(observability_module, "_query_retry_counts", fake_retries)

    snapshot = await observability_module.collect_outbox_backlog_snapshot(
        object(),
        tenant_id=uuid.uuid4(),
        event_type="campo.sync.falha",
    )

    data = snapshot.to_dict()

    assert captured["tenant_id"] is not None
    assert captured["event_type"] == "campo.sync.falha"
    assert "payload" not in data
    assert data["current_backlog"] == 3
    assert data["retries_seen"] == 4


def test_metrics_command_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_open_session(session_factory=None) -> object:  # noqa: ANN001
        return object()

    async def fake_close_session(session: object) -> None:  # noqa: ARG001
        return None

    async def fake_metrics(session: object, *, tenant_id=None, event_type=None, base_metrics=None):  # noqa: ANN001
        metrics = OutboxMetrics(started_at=datetime.now(outbox_worker_module.UTC))
        metrics.current_backlog = 7
        metrics.retries_seen = 2
        metrics.events_processed = 10
        metrics.batches_processed = 5
        metrics.errors = 1
        return metrics

    monkeypatch.setattr(outbox_worker_module, "_open_session", fake_open_session)
    monkeypatch.setattr(outbox_worker_module, "_close_session", fake_close_session)
    monkeypatch.setattr(outbox_worker_module, "collect_outbox_metrics", fake_metrics)

    exit_code = outbox_worker_module.main(["metrics", "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == outbox_worker_module.EXIT_OK
    assert output["current_backlog"] == 7
    assert output["retries_seen"] == 2


def test_health_command_outputs_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_open_session(session_factory=None) -> object:  # noqa: ANN001
        return object()

    async def fake_close_session(session: object) -> None:  # noqa: ARG001
        return None

    async def fake_health(session: object, *, tenant_id=None, event_type=None, base_metrics=None):  # noqa: ANN001
        metrics = OutboxMetrics(started_at=datetime.now(outbox_worker_module.UTC))
        metrics.current_backlog = 4
        return observability_module.evaluate_outbox_health(metrics)

    monkeypatch.setattr(outbox_worker_module, "_open_session", fake_open_session)
    monkeypatch.setattr(outbox_worker_module, "_close_session", fake_close_session)
    monkeypatch.setattr(outbox_worker_module, "collect_outbox_health", fake_health)

    exit_code = outbox_worker_module.main(["health"])
    output = capsys.readouterr().out

    assert exit_code == outbox_worker_module.EXIT_OK
    assert "Outbox Worker Health" in output
    assert "Status:" in output
