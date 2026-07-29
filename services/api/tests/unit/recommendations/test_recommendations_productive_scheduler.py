from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import InterfaceError

from recommendations import scheduler as scheduler_module
from recommendations.registry import RecommendationProviderRegistry
from recommendations.scheduler import RecommendationSchedulerResult, RecommendationSchedulerService


class AsyncSessionContext:
    """Small async context manager used to isolate worker scheduler tests."""

    def __init__(self, session: object) -> None:
        self.session = session

    async def __aenter__(self) -> object:
        return self.session

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


def _session_factory(session: object):
    return lambda: AsyncSessionContext(session)


def _result(tenant_id):
    return RecommendationSchedulerResult(
        scheduler_run_id=uuid4(),
        tenant_id=tenant_id,
        providers_requested=1,
        providers_executed=1,
        recommendations_created=1,
        recommendations_updated=0,
    )


@pytest.mark.asyncio
async def test_productive_cycle_runs_each_active_tenant_under_one_lock(monkeypatch) -> None:
    lock_session = SimpleNamespace()
    tenant_a = uuid4()
    tenant_b = uuid4()
    run_tenant = AsyncMock(return_value=SimpleNamespace())
    acquire_lock = AsyncMock(return_value=True)
    release_lock = AsyncMock()

    monkeypatch.setattr(scheduler_module, "async_session_maker", _session_factory(lock_session))
    monkeypatch.setattr(scheduler_module, "_acquire_scheduler_lock", acquire_lock)
    monkeypatch.setattr(scheduler_module, "_release_scheduler_lock", release_lock)
    monkeypatch.setattr(scheduler_module, "_list_active_tenant_ids", AsyncMock(return_value=[tenant_a, tenant_b]))
    monkeypatch.setattr(scheduler_module, "_run_tenant_cycle", run_tenant)

    completed = await scheduler_module.run_scheduled_recommendation_cycle(batch_size=2)

    assert completed == 2
    assert run_tenant.await_args_list[0].args[0] == tenant_a
    assert run_tenant.await_args_list[1].args[0] == tenant_b
    assert all(call.kwargs["batch_size"] == 2 for call in run_tenant.await_args_list)
    acquire_lock.assert_awaited_once_with(lock_session)
    release_lock.assert_awaited_once_with(lock_session)


@pytest.mark.asyncio
async def test_productive_cycle_skips_when_concurrent_lock_is_busy(monkeypatch) -> None:
    lock_session = SimpleNamespace()
    run_tenant = AsyncMock()

    monkeypatch.setattr(scheduler_module, "async_session_maker", _session_factory(lock_session))
    monkeypatch.setattr(scheduler_module, "_acquire_scheduler_lock", AsyncMock(return_value=False))
    monkeypatch.setattr(scheduler_module, "_run_tenant_cycle", run_tenant)

    completed = await scheduler_module.run_scheduled_recommendation_cycle()

    assert completed == 0
    run_tenant.assert_not_awaited()


@pytest.mark.asyncio
async def test_release_lock_ignores_already_closed_postgres_connection() -> None:
    session = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        execute=AsyncMock(
            side_effect=InterfaceError(
                "SELECT pg_advisory_unlock(:lock_id)",
                {"lock_id": 1},
                Exception("connection is closed"),
            )
        ),
        invalidate=AsyncMock(),
    )

    await scheduler_module._release_scheduler_lock(session)

    session.invalidate.assert_awaited_once()


@pytest.mark.asyncio
async def test_tenant_cycle_sets_and_clears_rls_context_and_commits(monkeypatch) -> None:
    tenant_id = uuid4()
    session = SimpleNamespace(
        info={},
        execute=AsyncMock(),
        rollback=AsyncMock(),
        commit=AsyncMock(),
        invalidate=AsyncMock(),
    )
    lifecycle = SimpleNamespace(expire_due_recommendations=AsyncMock(return_value=2))
    scheduler_service = SimpleNamespace(
        run_scheduled_recommendations=AsyncMock(return_value=_result(tenant_id))
    )

    monkeypatch.setattr(scheduler_module, "async_session_maker", _session_factory(session))
    monkeypatch.setattr(scheduler_module, "RecommendationLifecycleService", lambda *args: lifecycle)
    monkeypatch.setattr(scheduler_module, "RecommendationSchedulerService", lambda *args: scheduler_service)

    result = await scheduler_module._run_tenant_cycle(
        tenant_id,
        dry_run=False,
        batch_size=3,
        max_batches=1,
    )

    assert result is not None
    assert result.recommendations_expired == 2
    lifecycle.expire_due_recommendations.assert_awaited_once()
    scheduler_service.run_scheduled_recommendations.assert_awaited_once_with(
        tenant_id=tenant_id,
        dry_run=False,
        batch_size=3,
        max_batches=1,
    )
    assert session.execute.await_count == 2
    assert "set_config('app.current_tenant_id'" in str(session.execute.await_args_list[0].args[0])
    assert "RESET app.current_tenant_id" in str(session.execute.await_args_list[1].args[0])
    assert session.commit.await_count == 2
    assert session.rollback.await_count == 1
    assert session.info == {}


@pytest.mark.asyncio
async def test_tenant_cycle_dry_run_skips_expiration_and_persistence(monkeypatch) -> None:
    tenant_id = uuid4()
    session = SimpleNamespace(
        info={},
        execute=AsyncMock(),
        rollback=AsyncMock(),
        commit=AsyncMock(),
        invalidate=AsyncMock(),
    )
    lifecycle = SimpleNamespace(expire_due_recommendations=AsyncMock())
    scheduler_service = SimpleNamespace(
        run_scheduled_recommendations=AsyncMock(return_value=_result(tenant_id))
    )

    monkeypatch.setattr(scheduler_module, "async_session_maker", _session_factory(session))
    monkeypatch.setattr(scheduler_module, "RecommendationLifecycleService", lambda *args: lifecycle)
    monkeypatch.setattr(scheduler_module, "RecommendationSchedulerService", lambda *args: scheduler_service)

    result = await scheduler_module._run_tenant_cycle(
        tenant_id,
        dry_run=True,
        batch_size=1,
        max_batches=None,
    )

    assert result is not None
    assert result.recommendations_expired == 0
    lifecycle.expire_due_recommendations.assert_not_awaited()
    assert session.commit.await_count == 1
    assert session.rollback.await_count == 1


@pytest.mark.asyncio
async def test_tenant_cycle_contains_scheduler_failure(monkeypatch) -> None:
    tenant_id = uuid4()
    session = SimpleNamespace(
        info={},
        execute=AsyncMock(),
        rollback=AsyncMock(),
        commit=AsyncMock(),
        invalidate=AsyncMock(),
    )
    lifecycle = SimpleNamespace(expire_due_recommendations=AsyncMock(return_value=0))
    scheduler_service = SimpleNamespace(
        run_scheduled_recommendations=AsyncMock(side_effect=RuntimeError("provider batch failed"))
    )

    monkeypatch.setattr(scheduler_module, "async_session_maker", _session_factory(session))
    monkeypatch.setattr(scheduler_module, "RecommendationLifecycleService", lambda *args: lifecycle)
    monkeypatch.setattr(scheduler_module, "RecommendationSchedulerService", lambda *args: scheduler_service)

    result = await scheduler_module._run_tenant_cycle(
        tenant_id,
        dry_run=False,
        batch_size=1,
        max_batches=None,
    )

    assert result is None
    assert session.rollback.await_count == 2
    assert session.info == {}


@pytest.mark.asyncio
async def test_scheduler_returns_empty_result_without_registered_providers() -> None:
    scheduler = RecommendationSchedulerService(
        SimpleNamespace(),
        registry=RecommendationProviderRegistry(),
    )

    result = await scheduler.run_scheduled_recommendations(tenant_id=uuid4())

    assert result.providers_requested == 0
    assert result.providers_executed == 0
    assert result.warnings == ["no_providers_registered"]
