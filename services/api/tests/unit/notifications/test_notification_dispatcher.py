from __future__ import annotations

import inspect
import uuid
from unittest.mock import Mock

import pytest

import notifications.adapters as notifications_adapters_module
import notifications.dispatcher as notifications_dispatcher_module
from notifications import (
    LogNotificationAdapter,
    NoopNotificationAdapter,
    NotificationAdapter,
    NotificationAdapterNotRegisteredError,
    NotificationAdapterRegistry,
    NotificationChannel,
    NotificationDeliveryResult,
    NotificationDispatcher,
    NotificationDispatchResult,
    NotificationEvent,
    NotificationPriority,
    NotificationStatus,
)


class BrokenNotificationAdapter(NotificationAdapter):
    adapter_name = "broken"
    supported_channels = (NotificationChannel.LOG,)

    async def send(self, event: NotificationEvent) -> NotificationDeliveryResult:
        raise RuntimeError("adapter boom")


def test_notification_event_creation() -> None:
    event = NotificationEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        recipient_user_id=uuid.uuid4(),
        recipient_email="user@example.com",
        recipient_phone="+5511999999999",
        channel=NotificationChannel.LOG,
        priority=NotificationPriority.CRITICAL,
        subject="Subject",
        message="Message",
        source_type="ESG_CERTIFICACAO_VENCIDA",
        source_id="cert-1",
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
        metadata={"foo": "bar"},
    )

    assert event.notification_id is not None
    assert event.created_at.tzinfo is not None
    assert event.metadata["foo"] == "bar"


def test_registry_registers_and_resolves_channels() -> None:
    registry = NotificationAdapterRegistry()
    registry.register(LogNotificationAdapter)
    registry.register(NoopNotificationAdapter)

    assert registry.resolve(NotificationChannel.LOG) is LogNotificationAdapter
    assert registry.resolve(NotificationChannel.EMAIL) is NoopNotificationAdapter
    assert set(registry.list_supported_channels()) == {
        NotificationChannel.LOG,
        NotificationChannel.IN_APP,
        NotificationChannel.EMAIL,
        NotificationChannel.WHATSAPP,
        NotificationChannel.PUSH,
    }


@pytest.mark.asyncio
async def test_log_adapter_delivers_notification() -> None:
    event = NotificationEvent(
        tenant_id=uuid.uuid4(),
        channel=NotificationChannel.LOG,
        subject="Subject",
        message="Message",
        source_type="alert.created",
        source_id="1",
    )

    result = await LogNotificationAdapter().send(event)

    assert result.status == NotificationStatus.DELIVERED
    assert result.delivered is True
    assert result.skipped is False
    assert result.provider_message_id == f"log:{event.notification_id}"


@pytest.mark.asyncio
async def test_channel_without_adapter_returns_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = NotificationAdapterRegistry()
    dispatcher = NotificationDispatcher(registry=registry)
    event = NotificationEvent(
        tenant_id=uuid.uuid4(),
        channel=NotificationChannel.LOG,
        subject="Subject",
        message="Message",
        source_type="alert.created",
        source_id="1",
    )
    monkeypatch.setattr(
        registry,
        "resolve",
        Mock(side_effect=NotificationAdapterNotRegisteredError("LOG")),
    )

    result = await dispatcher.dispatch(event)

    assert result.status == NotificationStatus.NOT_IMPLEMENTED
    assert result.skipped is True
    assert result.failed is False
    assert "No notification adapter registered" in (result.error or "")


@pytest.mark.asyncio
async def test_dispatcher_isolates_adapter_failure() -> None:
    registry = NotificationAdapterRegistry()
    registry.register(BrokenNotificationAdapter)
    dispatcher = NotificationDispatcher(registry=registry)
    event = NotificationEvent(
        tenant_id=uuid.uuid4(),
        channel=NotificationChannel.LOG,
        priority=NotificationPriority.HIGH,
        subject="Subject",
        message="Message",
        source_type="alert.created",
        source_id="1",
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
    )

    result = await dispatcher.dispatch(event)

    assert result.status == NotificationStatus.FAILED
    assert result.failed is True
    assert result.delivered is False
    assert "RuntimeError" in (result.error or "")


@pytest.mark.asyncio
async def test_dispatcher_consolidates_result_and_preserves_metadata() -> None:
    registry = NotificationAdapterRegistry()
    registry.register(LogNotificationAdapter)
    dispatcher = NotificationDispatcher(registry=registry)
    correlation_id = uuid.uuid4()
    causation_id = uuid.uuid4()
    event = NotificationEvent(
        tenant_id=uuid.uuid4(),
        channel=NotificationChannel.LOG,
        priority=NotificationPriority.CRITICAL,
        subject="Subject",
        message="Message",
        source_type="alert.created",
        source_id="1",
        correlation_id=correlation_id,
        causation_id=causation_id,
        metadata={"origin": "test"},
    )

    result = await dispatcher.dispatch(event)

    assert isinstance(result, NotificationDispatchResult)
    assert result.status == NotificationStatus.DELIVERED
    assert result.priority == NotificationPriority.CRITICAL
    assert result.correlation_id == correlation_id
    assert result.causation_id == causation_id
    assert result.delivered is True
    assert result.metadata["origin"] == "test"


def test_dispatcher_and_adapters_do_not_know_alert_engine() -> None:
    dispatcher_source = inspect.getsource(notifications_dispatcher_module)
    adapters_source = inspect.getsource(notifications_adapters_module)

    assert "AlertLifecycleService" not in dispatcher_source
    assert "alert_engine" not in adapters_source
