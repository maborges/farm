"""Testes isolados dos guardrails de clima; não iniciam DB, Redis ou provedores."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from core.config import settings
from public_clima.adapters import verify_provider_public_authorization
from public_clima.cache import ClimaCache, ClimaCacheEntry
from public_clima.contracts import ClimaPrevisaoResponse
from public_clima.dynamic_orchestrator import DynamicWeatherOrchestrator


def test_weatherapi_requires_explicit_enable_even_with_credential(monkeypatch):
    monkeypatch.setattr(settings, "weatherapi_api_key", "synthetic-test-key")
    monkeypatch.setattr(settings, "weatherapi_enabled", False)
    allowed, _ = verify_provider_public_authorization(
        "WEATHERAPI", credentials={"WEATHERAPI": "synthetic-test-key"}
    )
    assert not allowed

    monkeypatch.setattr(settings, "weatherapi_enabled", True)
    allowed, _ = verify_provider_public_authorization(
        "WEATHERAPI", credentials={"WEATHERAPI": "synthetic-test-key"}
    )
    assert allowed


def test_environment_config_source_does_not_open_database(monkeypatch):
    import public_clima.dynamic_orchestrator as module

    monkeypatch.setattr(settings, "clima_config_source", "environment")
    monkeypatch.setattr(settings, "clima_active_provider", "WEATHERAPI")
    monkeypatch.setattr(settings, "weatherapi_enabled", False)
    monkeypatch.setattr(settings, "weatherapi_api_key", "")
    session_factory = AsyncMock(side_effect=AssertionError("DB must not be accessed"))
    monkeypatch.setattr(module, "async_session_maker", session_factory)

    cache = AsyncMock()
    orchestrator = DynamicWeatherOrchestrator(cache=cache)
    monkeypatch.setattr(orchestrator, "_rebuild_adapters", lambda: None)
    asyncio.run(orchestrator.refresh_config())

    session_factory.assert_not_called()
    assert orchestrator._config.active_provider == "WEATHERAPI"
    assert orchestrator._config.fallback_chain == []


def test_cache_does_not_return_stale_payload_after_one_hour():
    cache = ClimaCache.__new__(ClimaCache)
    cache.local_last = {}
    cache.local_fresh = {}
    cache.single_worker_fallback = True
    response = ClimaPrevisaoResponse(
        latitude=0,
        longitude=0,
        latitudeGrid=0,
        longitudeGrid=0,
        fusoHorario="UTC",
        provedor="TEST",
        licencaFonte="synthetic",
        tipoDado="PREVISTO",
        dadosSinteticos=True,
        previsaoHoraria=[],
        previsaoDiaria=[],
        horarioReferenciaIso="2026-10-26T00:00:00Z",
        obtidoEmIso="2026-10-26T00:00:00Z",
        validoAteIso="2026-10-26T00:30:00Z",
        emCache=False,
        desatualizado=False,
        statusOperacional="NORMAL",
        avisoLegal="synthetic",
    )
    entry = ClimaCacheEntry(
        response=response,
        synced_at=datetime.now(timezone.utc) - timedelta(hours=1, seconds=1),  # noqa: UP017
    )
    cache.local_last["key"] = (entry, 0)
    assert asyncio.run(cache.get_last("key", shared=False)) is None
    assert "key" not in cache.local_last

