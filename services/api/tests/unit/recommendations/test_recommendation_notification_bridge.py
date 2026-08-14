from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from notifications import (
    NotificationDeduplicationStore,
    NotificationDispatcher,
    NotificationPolicy,
    NotificationPolicyRegistry,
    NotificationPolicyResult,
    NotificationPolicyService,
    NotificationPriority,
    NotificationSilenceWindow,
    NotificationStatus,
)
from recommendations.notification_bridge import (
    RECOMMENDATION_NOTIFICATION_EVENT_TYPE,
    RecommendationNotificationBridge,
)

UTC = timezone.utc  # noqa: UP017


class BlockedRecommendationPolicy(NotificationPolicy):
    event_type = RECOMMENDATION_NOTIFICATION_EVENT_TYPE

    def evaluate(self, event, preferences=None):  # type: ignore[override]
        return NotificationPolicyResult(
            allowed=False,
            reason="policy_blocked",
            tenant_id=event.tenant_id,
            event_type=self.resolve_event_type(event),
            priority=NotificationPriority.HIGH.value,
            channels=["LOG"],
            recipients=[],
            dedupe_key="blocked",
            silence_window_applied=False,
        )


class FailingDispatcher:
    async def dispatch(self, event):  # pragma: no cover - exercised via bridge
        raise RuntimeError("boom")


def _recommendation(
    *,
    priority: str = "HIGH",
    status: str = "CREATED",
    expires_at: datetime | None = None,
    tenant_id: uuid.UUID | None = None,
    dedupe_key: str = "tenant:scope:rule",
) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain="AGRICULTURE",
        status=status,
        priority=priority,
        source_type="SIGNAL",
        action_type="OPEN_ROUTE",
        provider_name="provider",
        rule_code="RULE_1",
        scope_type="SAFRA",
        scope_id="scope-1",
        title="Revisar custo",
        summary="Resumo",
        rationale="Racional",
        dedupe_key=dedupe_key,
        source_signal_ids=[uuid.uuid4()],
        confidence=None,
        action_label="Abrir",
        action_target="/dashboard",
        context={},
        expires_at=expires_at,
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


@pytest.mark.asyncio
async def test_bridge_dispatches_high_priority_recommendation() -> None:
    recommendation = _recommendation(priority="HIGH")
    bridge = RecommendationNotificationBridge()

    result = await bridge.notify(recommendation)

    assert result.eligible is True
    assert result.reason is None
    assert result.dispatch_result is not None
    assert result.dispatch_result.status == NotificationStatus.DELIVERED
    assert result.dispatch_result.delivered is True
    assert (
        result.dispatch_result.metadata["policy"]["event_type"]
        == RECOMMENDATION_NOTIFICATION_EVENT_TYPE
    )
    assert (
        result.dispatch_result.metadata["policy"]["dedupe_key"]
        == "recommendation:tenant:scope:rule"
    )


@pytest.mark.asyncio
async def test_bridge_skips_low_priority_recommendation() -> None:
    recommendation = _recommendation(priority="NORMAL")
    bridge = RecommendationNotificationBridge()

    result = await bridge.notify(recommendation)

    assert result.eligible is False
    assert result.reason == "priority_not_eligible"
    assert result.dispatch_result is None


@pytest.mark.asyncio
async def test_bridge_skips_expired_recommendation() -> None:
    recommendation = _recommendation(
        priority="HIGH",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    bridge = RecommendationNotificationBridge()

    result = await bridge.notify(recommendation)

    assert result.eligible is False
    assert result.reason == "expired"
    assert result.dispatch_result is None


@pytest.mark.asyncio
async def test_bridge_deduplication_suppresses_repeat_dispatch() -> None:
    recommendation = _recommendation(priority="URGENT")
    bridge = RecommendationNotificationBridge()

    first = await bridge.notify(recommendation)
    second = await bridge.notify(recommendation)

    assert first.dispatch_result is not None
    assert first.dispatch_result.status == NotificationStatus.DELIVERED
    assert second.dispatch_result is not None
    assert second.dispatch_result.status == NotificationStatus.SKIPPED
    assert second.dispatch_result.error == "duplicate_notification_suppressed"


@pytest.mark.asyncio
async def test_bridge_policy_block_prevents_delivery() -> None:
    recommendation = _recommendation(priority="HIGH")
    policy_registry = NotificationPolicyRegistry()
    policy_registry.register(BlockedRecommendationPolicy())
    dispatcher = NotificationDispatcher(
        policy_service=NotificationPolicyService(
            registry=policy_registry,
            deduplication_store=NotificationDeduplicationStore(),
            silence_window=NotificationSilenceWindow(
                clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
            ),
        ),
    )
    bridge = RecommendationNotificationBridge(dispatcher=dispatcher)

    result = await bridge.notify(recommendation)

    assert result.eligible is True
    assert result.dispatch_result is not None
    assert result.dispatch_result.status == NotificationStatus.SKIPPED
    assert result.dispatch_result.skipped is True
    assert result.dispatch_result.error == "policy_blocked"
    assert result.dispatch_result.metadata["policy"]["allowed"] is False


@pytest.mark.asyncio
async def test_bridge_dispatcher_failure_isolated() -> None:
    recommendation = _recommendation(priority="HIGH")
    bridge = RecommendationNotificationBridge(dispatcher=FailingDispatcher())

    result = await bridge.notify(recommendation)

    assert result.eligible is True
    assert result.reason == "dispatch_failed"
    assert result.dispatch_result is None


def test_bridge_does_not_import_alert_engine() -> None:
    source = inspect.getsource(RecommendationNotificationBridge)

    assert "alert_engine" not in source


def _mock_session_sem_existente():
    from unittest.mock import AsyncMock, MagicMock

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_bridge_persiste_notificacao_quando_session_informada() -> None:
    """Recomendação elegível deve gravar em `notificacoes`, não só dispatch via policy engine."""
    from unittest.mock import AsyncMock, patch

    recommendation = _recommendation(priority="URGENT")
    bridge = RecommendationNotificationBridge()
    session = _mock_session_sem_existente()

    with patch(
        "recommendations.notification_bridge.NotificacaoService.criar_e_push",
        new=AsyncMock(return_value=None),
    ) as mock_criar:
        result = await bridge.notify(recommendation, session=session)

    assert result.eligible is True
    mock_criar.assert_awaited_once()
    dados = mock_criar.call_args.args[0]
    assert dados.tipo == "RECOMENDACAO"
    assert dados.origem == "recommendation"
    assert dados.origem_id == str(recommendation.id)
    assert dados.nivel == "DANGER"  # URGENT -> DANGER


@pytest.mark.asyncio
async def test_bridge_sem_session_nao_persiste_notificacao() -> None:
    """Sem session (chamadores legados), o bridge continua só despachando via policy engine."""
    from unittest.mock import AsyncMock, patch

    recommendation = _recommendation(priority="HIGH")
    bridge = RecommendationNotificationBridge()

    with patch(
        "recommendations.notification_bridge.NotificacaoService.criar_e_push",
        new=AsyncMock(),
    ) as mock_criar:
        result = await bridge.notify(recommendation)

    assert result.eligible is True
    mock_criar.assert_not_awaited()


@pytest.mark.asyncio
async def test_bridge_falha_ao_persistir_nao_derruba_dispatch() -> None:
    """Erro ao gravar em `notificacoes` não deve impedir o dispatch da policy engine (isolamento defensivo)."""
    from unittest.mock import AsyncMock, patch

    recommendation = _recommendation(priority="HIGH")
    bridge = RecommendationNotificationBridge()
    session = _mock_session_sem_existente()

    with patch(
        "recommendations.notification_bridge.NotificacaoService.criar_e_push",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        result = await bridge.notify(recommendation, session=session)

    assert result.eligible is True
    assert result.dispatch_result is not None
    assert result.dispatch_result.delivered is True
