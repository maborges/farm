from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from notifications import (
    DefaultNotificationPolicy,
    NotificationAdapter,
    NotificationAdapterRegistry,
    NotificationChannel,
    NotificationDeduplicationStore,
    NotificationDeliveryResult,
    NotificationDispatcher,
    NotificationEvent,
    NotificationPolicy,
    NotificationPolicyRegistry,
    NotificationPolicyResult,
    NotificationPolicyService,
    NotificationPreferences,
    NotificationPriority,
    NotificationSilenceWindow,
    NotificationStatus,
)

UTC = timezone.utc  # noqa: UP017


class AllowedChannelPolicy(NotificationPolicy):
    event_type = "notifications.channels"

    def resolve_channels(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> list[str]:
        return ["LOG", "NOOP"]

    def resolve_dedupe_key(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> str | None:
        return None


class BlockedPolicy(NotificationPolicy):
    event_type = "notifications.blocked"

    def evaluate(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> NotificationPolicyResult:
        return NotificationPolicyResult(
            allowed=False,
            reason="manual_suppression",
            tenant_id=event.tenant_id,
            event_type="notifications.blocked",
            priority="NORMAL",
            channels=["LOG"],
            recipients=[],
            dedupe_key=None,
            silence_window_applied=False,
        )


class PriorityPolicy(NotificationPolicy):
    event_type = "notifications.priority"

    def resolve_priority(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> NotificationPriority:
        return NotificationPriority.CRITICAL

    def resolve_dedupe_key(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> str | None:
        return None


class DedupePolicy(NotificationPolicy):
    event_type = "notifications.dedupe"


class SpyAdapter(NotificationAdapter):
    adapter_name = "spy"
    supported_channels = (NotificationChannel.LOG, NotificationChannel.NOOP)
    calls: list[NotificationChannel] = []

    async def send(self, event: NotificationEvent) -> NotificationDeliveryResult:
        self.calls.append(event.channel)
        return self._deliver(event)

    def _deliver(self, event: NotificationEvent) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=event.channel,
            status=NotificationStatus.DELIVERED,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            delivered=True,
            metadata={"adapter_name": self.adapter_name},
        )


def _event(
    event_type: str,
    *,
    tenant_id: uuid.UUID | None = None,
    source_id: str = "source-1",
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> NotificationEvent:
    return NotificationEvent(
        tenant_id=tenant_id or uuid.uuid4(),
        channel=NotificationChannel.LOG,
        priority=priority,
        subject="Subject",
        message="Message",
        source_type="ALERT_CREATED",
        source_id=source_id,
        metadata={"event_type": event_type},
    )


def test_default_policy_allows_log_only() -> None:
    event = _event("notifications.default")

    result = DefaultNotificationPolicy().evaluate(event)

    assert result.allowed is True
    assert result.priority == "NORMAL"
    assert result.channels == ["LOG"]
    assert result.recipients == []
    assert result.dedupe_key is None


def test_registry_returns_specific_policy_by_event_type() -> None:
    registry = NotificationPolicyRegistry()
    policy = AllowedChannelPolicy()
    registry.register(policy)

    assert registry.get_policy("notifications.channels") is policy


def test_registry_falls_back_to_default_policy() -> None:
    registry = NotificationPolicyRegistry()

    assert isinstance(registry.get_policy("unknown.event"), DefaultNotificationPolicy)


def test_policy_service_uses_fallback_policy_for_unknown_event_type() -> None:
    service = NotificationPolicyService(
        registry=NotificationPolicyRegistry(),
        deduplication_store=NotificationDeduplicationStore(),
        silence_window=NotificationSilenceWindow(
            clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
        ),
    )

    result = service.evaluate(_event("unknown.event"))

    assert result.allowed is True
    assert result.channels == ["LOG"]
    assert result.reason is None


def test_policy_service_can_suppress_event() -> None:
    registry = NotificationPolicyRegistry()
    registry.register(BlockedPolicy())
    service = NotificationPolicyService(
        registry=registry,
        deduplication_store=NotificationDeduplicationStore(),
        silence_window=NotificationSilenceWindow(
            clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
        ),
    )

    result = service.evaluate(_event("notifications.blocked"))

    assert result.allowed is False
    assert result.reason == "manual_suppression"
    assert result.silence_window_applied is False


def test_policy_service_resolves_priority_correctly() -> None:
    registry = NotificationPolicyRegistry()
    registry.register(PriorityPolicy())
    service = NotificationPolicyService(
        registry=registry,
        deduplication_store=NotificationDeduplicationStore(),
        silence_window=NotificationSilenceWindow(
            clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
        ),
    )

    result = service.evaluate(_event("notifications.priority"))

    assert result.priority == "CRITICAL"


def test_dedupe_blocks_duplicate_in_same_tenant() -> None:
    registry = NotificationPolicyRegistry()
    registry.register(DedupePolicy())
    service = NotificationPolicyService(
        registry=registry,
        deduplication_store=NotificationDeduplicationStore(),
        silence_window=NotificationSilenceWindow(
            clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
        ),
    )
    event = _event("notifications.dedupe", source_id="shared")

    first = service.evaluate(event)
    second = service.evaluate(event)

    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "duplicate_notification_suppressed"


def test_dedupe_does_not_block_different_events() -> None:
    registry = NotificationPolicyRegistry()
    registry.register(DedupePolicy())
    service = NotificationPolicyService(
        registry=registry,
        deduplication_store=NotificationDeduplicationStore(),
        silence_window=NotificationSilenceWindow(
            clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
        ),
    )
    event_a = _event("notifications.dedupe", source_id="a")
    event_b = _event("notifications.dedupe", source_id="b")

    assert service.evaluate(event_a).allowed is True
    assert service.evaluate(event_b).allowed is True


def test_dedupe_is_scoped_by_tenant() -> None:
    registry = NotificationPolicyRegistry()
    registry.register(DedupePolicy())
    service = NotificationPolicyService(
        registry=registry,
        deduplication_store=NotificationDeduplicationStore(),
        silence_window=NotificationSilenceWindow(
            clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
        ),
    )
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    event_a = _event("notifications.dedupe", tenant_id=tenant_a, source_id="shared")
    event_b = _event("notifications.dedupe", tenant_id=tenant_b, source_id="shared")

    assert service.evaluate(event_a).allowed is True
    assert service.evaluate(event_b).allowed is True


def test_silence_window_blocks_low_and_normal() -> None:
    registry = NotificationPolicyRegistry()
    registry.register(DedupePolicy())
    service = NotificationPolicyService(
        registry=registry,
        deduplication_store=NotificationDeduplicationStore(),
        silence_window=NotificationSilenceWindow(
            clock=lambda: datetime(2026, 6, 26, 23, tzinfo=UTC)
        ),
    )

    result = service.evaluate(
        _event("notifications.dedupe", priority=NotificationPriority.NORMAL)
    )

    assert result.allowed is False
    assert result.reason == "silence_window_suppressed"
    assert result.silence_window_applied is True


def test_silence_window_allows_critical() -> None:
    registry = NotificationPolicyRegistry()
    registry.register(DedupePolicy())
    service = NotificationPolicyService(
        registry=registry,
        deduplication_store=NotificationDeduplicationStore(),
        silence_window=NotificationSilenceWindow(
            clock=lambda: datetime(2026, 6, 26, 23, tzinfo=UTC)
        ),
    )

    result = service.evaluate(
        _event("notifications.dedupe", priority=NotificationPriority.CRITICAL)
    )

    assert result.allowed is True


@pytest.mark.asyncio
async def test_dispatcher_respects_allowed_false() -> None:
    registry = NotificationAdapterRegistry()
    registry.register(SpyAdapter)
    policy_registry = NotificationPolicyRegistry()
    policy_registry.register(BlockedPolicy())
    dispatcher = NotificationDispatcher(
        registry=registry,
        policy_service=NotificationPolicyService(
            registry=policy_registry,
            deduplication_store=NotificationDeduplicationStore(),
            silence_window=NotificationSilenceWindow(
                clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
            ),
        ),
    )
    SpyAdapter.calls.clear()

    result = await dispatcher.dispatch(_event("notifications.blocked"))

    assert result.status == NotificationStatus.SKIPPED
    assert result.skipped is True
    assert SpyAdapter.calls == []
    assert result.metadata["policy"]["reason"] == "manual_suppression"


@pytest.mark.asyncio
async def test_dispatcher_uses_channels_resolved_by_policy() -> None:
    registry = NotificationAdapterRegistry()
    registry.register(SpyAdapter)
    policy_registry = NotificationPolicyRegistry()
    policy_registry.register(AllowedChannelPolicy())
    dispatcher = NotificationDispatcher(
        registry=registry,
        policy_service=NotificationPolicyService(
            registry=policy_registry,
            deduplication_store=NotificationDeduplicationStore(),
            silence_window=NotificationSilenceWindow(
                clock=lambda: datetime(2026, 6, 26, 12, tzinfo=UTC)
            ),
        ),
    )
    SpyAdapter.calls.clear()

    result = await dispatcher.dispatch(_event("notifications.channels"))

    assert result.status == NotificationStatus.DELIVERED
    assert SpyAdapter.calls == [NotificationChannel.LOG, NotificationChannel.NOOP]
    assert [delivery["channel"] for delivery in result.metadata["deliveries"]] == [
        "LOG",
        "NOOP",
    ]
