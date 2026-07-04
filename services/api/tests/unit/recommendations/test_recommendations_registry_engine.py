from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import recommendations.notification_bridge as notification_bridge_module
from recommendations.engine import RecommendationEngine
from recommendations.provider import RecommendationProvider
from recommendations.registry import RecommendationProviderRegistry
from recommendations.schemas import (
    OperationalContext,
    RecommendationCandidate,
    RecommendationSignal,
)


class FakeProvider(RecommendationProvider):
    provider_name = "fake"
    domains = ("AGRICULTURE",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        return [
            RecommendationCandidate(
                tenant_id=context.tenant_id,
                unidade_produtiva_id=context.unidade_produtiva_id,
                domain=context.domain,
                priority="HIGH",
                source_type="SIGNAL",
                action_type="OPEN_ROUTE",
                provider_name=self.provider_name,
                rule_code="RULE_FAKE",
                scope_type=context.scope_type,
                scope_id=context.scope_id,
                title="Revisar custo",
                summary="Resumo",
                rationale="Racional",
                dedupe_key=f"{context.scope_id}:rule_fake",
                source_signal_ids=[signal.signal_id for signal in signals],
                action_target="/dashboard/agricola",
            )
        ]


class FailingProvider(RecommendationProvider):
    provider_name = "failing"
    domains = ("AGRICULTURE",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        raise RuntimeError("boom")


def test_registry_registers_and_filters_by_domain() -> None:
    registry = RecommendationProviderRegistry()
    registry.register(FakeProvider)

    assert registry.get_provider("fake") is FakeProvider
    assert registry.find_by_domain("AGRICULTURE") == (FakeProvider,)
    assert registry.find_by_domain("FINANCE") == ()


def test_registry_rejects_duplicate_registration() -> None:
    registry = RecommendationProviderRegistry()
    registry.register(FakeProvider)
    with pytest.raises(ValueError):
        registry.register(FakeProvider)


@pytest.mark.asyncio
async def test_engine_executes_provider_without_real_db() -> None:
    registry = RecommendationProviderRegistry()
    registry.register(FakeProvider)
    session = SimpleNamespace()
    engine = RecommendationEngine(session, uuid.uuid4(), registry=registry)
    now = datetime.now(timezone.utc)
    context = OperationalContext(
        tenant_id=engine.tenant_id,
        unidade_produtiva_id=None,
        domain="AGRICULTURE",
        scope_type="SAFRA",
        scope_id="safra-1",
        generated_at=now,
    )
    signals = [
        RecommendationSignal(
            signal_id=uuid.uuid4(),
            tenant_id=engine.tenant_id,
            domain="AGRICULTURE",
            source_type="SIGNAL",
            key="signal-1",
            occurred_at=now,
        )
    ]
    persisted = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=engine.tenant_id,
        unidade_produtiva_id=None,
        domain="AGRICULTURE",
        status="CREATED",
        priority="HIGH",
        source_type="SIGNAL",
        action_type="OPEN_ROUTE",
        provider_name="fake",
        rule_code="RULE_FAKE",
        scope_type="SAFRA",
        scope_id="safra-1",
        title="Revisar custo",
        summary="Resumo",
        rationale="Racional",
        dedupe_key="safra-1:rule_fake",
        source_signal_ids=[signals[0].signal_id],
        confidence=None,
        action_label=None,
        action_target="/dashboard/agricola",
        context={},
        expires_at=None,
        viewed_at=None,
        accepted_at=None,
        dismissed_at=None,
        postponed_until=None,
        executed_at=None,
        expired_at=None,
        superseded_at=None,
        superseded_by_id=None,
        created_at=now,
        updated_at=now,
    )
    engine.lifecycle._find_active_recommendation = AsyncMock(return_value=None)
    engine.lifecycle.create_or_update_recommendation = AsyncMock(return_value=persisted)

    result = await engine.generate(context, signals)

    assert result.providers_executed == 1
    assert result.recommendations_created == 1
    assert result.errors == 0
    assert len(result.items) == 1
    assert result.items[0].provider_name == "fake"
    engine.lifecycle._find_active_recommendation.assert_awaited_once()
    engine.lifecycle.create_or_update_recommendation.assert_awaited_once()


@pytest.mark.asyncio
async def test_engine_records_provider_failure_without_raising() -> None:
    registry = RecommendationProviderRegistry()
    registry.register(FailingProvider)
    session = SimpleNamespace()
    engine = RecommendationEngine(session, uuid.uuid4(), registry=registry)
    context = OperationalContext(
        tenant_id=engine.tenant_id,
        unidade_produtiva_id=None,
        domain="AGRICULTURE",
        scope_type="SAFRA",
        scope_id="safra-1",
        generated_at=datetime.now(timezone.utc),
    )

    result = await engine.generate(context, [])

    assert result.providers_executed == 1
    assert result.errors == 1
    assert result.recommendations_created == 0
    assert result.executions[0].status == "failed"


@pytest.mark.asyncio
async def test_engine_ignores_notification_bridge_failure() -> None:
    registry = RecommendationProviderRegistry()
    registry.register(FakeProvider)
    session = SimpleNamespace()
    engine = RecommendationEngine(session, uuid.uuid4(), registry=registry)
    now = datetime.now(timezone.utc)
    context = OperationalContext(
        tenant_id=engine.tenant_id,
        unidade_produtiva_id=None,
        domain="AGRICULTURE",
        scope_type="SAFRA",
        scope_id="safra-1",
        generated_at=now,
    )
    signals = [
        RecommendationSignal(
            signal_id=uuid.uuid4(),
            tenant_id=engine.tenant_id,
            domain="AGRICULTURE",
            source_type="SIGNAL",
            key="signal-1",
            occurred_at=now,
        )
    ]
    persisted = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=engine.tenant_id,
        unidade_produtiva_id=None,
        domain="AGRICULTURE",
        status="CREATED",
        priority="HIGH",
        source_type="SIGNAL",
        action_type="OPEN_ROUTE",
        provider_name="fake",
        rule_code="RULE_FAKE",
        scope_type="SAFRA",
        scope_id="safra-1",
        title="Revisar custo",
        summary="Resumo",
        rationale="Racional",
        dedupe_key="safra-1:rule_fake",
        source_signal_ids=[signals[0].signal_id],
        confidence=None,
        action_label=None,
        action_target="/dashboard/agricola",
        context={},
        expires_at=None,
        viewed_at=None,
        accepted_at=None,
        dismissed_at=None,
        postponed_until=None,
        executed_at=None,
        expired_at=None,
        superseded_at=None,
        superseded_by_id=None,
        created_at=now,
        updated_at=now,
    )
    engine.lifecycle._find_active_recommendation = AsyncMock(return_value=None)
    engine.lifecycle.create_or_update_recommendation = AsyncMock(return_value=persisted)

    class RaisingBridge:
        async def notify(self, recommendation, *, was_created=True):  # noqa: ARG002
            raise RuntimeError("boom")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        notification_bridge_module,
        "RecommendationNotificationBridge",
        RaisingBridge,
    )
    try:
        result = await engine.generate(context, signals)
    finally:
        monkeypatch.undo()

    assert result.providers_executed == 1
    assert result.recommendations_created == 1
    assert result.errors == 0
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_engine_does_not_notify_on_update() -> None:
    registry = RecommendationProviderRegistry()
    registry.register(FakeProvider)
    session = SimpleNamespace()
    engine = RecommendationEngine(session, uuid.uuid4(), registry=registry)
    now = datetime.now(timezone.utc)
    context = OperationalContext(
        tenant_id=engine.tenant_id,
        unidade_produtiva_id=None,
        domain="AGRICULTURE",
        scope_type="SAFRA",
        scope_id="safra-1",
        generated_at=now,
    )
    signals = [
        RecommendationSignal(
            signal_id=uuid.uuid4(),
            tenant_id=engine.tenant_id,
            domain="AGRICULTURE",
            source_type="SIGNAL",
            key="signal-1",
            occurred_at=now,
        )
    ]
    persisted = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=engine.tenant_id,
        unidade_produtiva_id=None,
        domain="AGRICULTURE",
        status="CREATED",
        priority="HIGH",
        source_type="SIGNAL",
        action_type="OPEN_ROUTE",
        provider_name="fake",
        rule_code="RULE_FAKE",
        scope_type="SAFRA",
        scope_id="safra-1",
        title="Revisar custo",
        summary="Resumo",
        rationale="Racional",
        dedupe_key="safra-1:rule_fake",
        source_signal_ids=[signals[0].signal_id],
        confidence=None,
        action_label=None,
        action_target="/dashboard/agricola",
        context={},
        expires_at=None,
        viewed_at=None,
        accepted_at=None,
        dismissed_at=None,
        postponed_until=None,
        executed_at=None,
        expired_at=None,
        superseded_at=None,
        superseded_by_id=None,
        created_at=now,
        updated_at=now,
    )
    engine.lifecycle._find_active_recommendation = AsyncMock(return_value=persisted)
    engine.lifecycle.create_or_update_recommendation = AsyncMock(return_value=persisted)

    class BridgeSpy:
        calls: list[object] = []

        async def notify(self, recommendation, *, was_created=True):  # noqa: ARG002
            self.calls.append(recommendation)
            return SimpleNamespace(eligible=True, reason=None, dispatch_result=None)

    bridge_spy = BridgeSpy()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        notification_bridge_module,
        "RecommendationNotificationBridge",
        lambda: bridge_spy,
    )
    try:
        result = await engine.generate(context, signals)
    finally:
        monkeypatch.undo()

    assert result.providers_executed == 1
    assert result.recommendations_created == 0
    assert result.recommendations_updated == 1
    assert bridge_spy.calls == []
