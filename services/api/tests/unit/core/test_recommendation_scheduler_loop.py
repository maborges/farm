from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core import background_jobs


@pytest.mark.asyncio
async def test_recommendation_scheduler_loop_disabled_when_dispatcher_is_none(monkeypatch) -> None:
    """When RECOMMENDATION_DISPATCHER_DATABASE_URL is unset (dispatcher_engine is None),

    the loop should log an informative message and return cleanly without exceptions.
    """
    import core.database

    monkeypatch.setattr(core.database, "dispatcher_engine", None)

    mock_cycle = AsyncMock()
    with patch(
        "recommendations.scheduler.run_scheduled_recommendation_cycle",
        mock_cycle,
    ):
        await background_jobs.run_recommendation_scheduler_loop()

    mock_cycle.assert_not_awaited()


@pytest.mark.asyncio
async def test_recommendation_scheduler_loop_runs_cycle_when_dispatcher_is_present(monkeypatch) -> None:
    """When dispatcher_engine is configured, the loop executes the cycle."""
    import core.database

    monkeypatch.setattr(core.database, "dispatcher_engine", object())

    cycle_called = False

    async def mock_cycle():
        nonlocal cycle_called
        cycle_called = True
        return 2

    # Patch sleep to raise CancelledError after first cycle to break infinite loop
    async def mock_sleep(seconds: float):
        raise asyncio.CancelledError()

    with (
        patch(
            "recommendations.scheduler.run_scheduled_recommendation_cycle",
            side_effect=mock_cycle,
        ),
        patch("asyncio.sleep", side_effect=mock_sleep),
    ):
        await background_jobs.run_recommendation_scheduler_loop()

    assert cycle_called is True

