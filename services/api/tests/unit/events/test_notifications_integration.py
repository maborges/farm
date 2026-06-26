from __future__ import annotations

import inspect
import uuid
from typing import Any, cast

import pytest

import notifications.subscribers as notifications_subscribers_module
from alert_engine.models import Domain
from events import DomainEvent, EventPublisher, EventSubscriberRegistry
from notifications import (
    LogNotificationAdapter,
    NotificationChannel,
    NotificationDispatcher,
    NotificationDispatchResult,
    NotificationEvent,
    NotificationEventSubscriber,
    NotificationPriority,
    NotificationStatus,
)


def test_domain_event_maps_to_notification_event() -> None:
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.SYSTEM,
        event_type="alerts.created",
        source_type="ALERT_CREATED",
        entity_type="operational_alert",
        entity_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
        metadata={
            "channel": "LOG",
            "recipient_email": "user@example.com",
            "subject": "Subject",
            "message": "Message",
        },
    )

    notification = NotificationEventSubscriber()._to_notification_event(event)

    assert isinstance(notification, NotificationEvent)
    assert notification.tenant_id == event.tenant_id
    assert notification.unidade_produtiva_id == event.unidade_produtiva_id
    assert notification.channel == NotificationChannel.LOG
    assert notification.priority == NotificationPriority.NORMAL
    assert notification.correlation_id == event.correlation_id
    assert notification.causation_id == event.causation_id
    assert notification.metadata["event_type"] == event.event_type
    assert notification.source_id == str(event.entity_id)


@pytest.mark.asyncio
async def test_event_publisher_dispatches_to_notification_subscriber(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = EventSubscriberRegistry()
    registered_subscriber = cast(Any, NotificationEventSubscriber)
    registry.register(registered_subscriber)
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.SYSTEM,
        event_type="notifications.dispatch",
        source_type="ALERT_CREATED",
        entity_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
        metadata={
            "channel": "LOG",
            "subject": "Subject",
            "message": "Message",
            "recipient_email": "user@example.com",
        },
    )

    class DispatcherSpy:
        def __init__(self) -> None:
            self.calls: list[NotificationEvent] = []

        async def dispatch(
            self,
            notification_event: NotificationEvent,
        ) -> NotificationDispatchResult:
            self.calls.append(notification_event)
            return NotificationDispatchResult(
                notification_id=notification_event.notification_id,
                channel=notification_event.channel,
                status=NotificationStatus.DELIVERED,
                priority=notification_event.priority,
                correlation_id=notification_event.correlation_id,
                causation_id=notification_event.causation_id,
                delivered=True,
                metadata={"adapter": "spy"},
            )

    dispatcher_spy = DispatcherSpy()
    monkeypatch.setattr(
        notifications_subscribers_module,
        "NotificationDispatcher",
        lambda: dispatcher_spy,
    )

    result = await EventPublisher(
        session=cast(Any, object()),
        registry=registry,
    ).publish(event)

    assert result.executed == 1
    assert result.succeeded == 1
    assert result.failed == 0
    assert dispatcher_spy.calls[0].metadata["event_type"] == event.event_type
    assert dispatcher_spy.calls[0].correlation_id == event.correlation_id
    assert dispatcher_spy.calls[0].causation_id == event.causation_id
    assert result.executions[0].metadata["notification_id"]


def test_notification_subscriber_registration_is_explicit() -> None:
    registry = EventSubscriberRegistry()
    registered_subscriber = cast(Any, NotificationEventSubscriber)
    registry.register(registered_subscriber)

    assert registry.find_by_event_type("notifications.dispatch") == (
        registered_subscriber,
    )
    assert registry.list_subscribers() == (registered_subscriber,)


def test_notification_dispatcher_and_subscriber_do_not_import_alert_engine() -> None:
    dispatcher_source = inspect.getsource(NotificationDispatcher)
    subscriber_source = inspect.getsource(NotificationEventSubscriber)

    assert "AlertLifecycleService" not in dispatcher_source
    assert "alert_engine" not in subscriber_source


@pytest.mark.asyncio
async def test_notification_dispatcher_chain_uses_log_adapter() -> None:
    event = NotificationEvent(
        tenant_id=uuid.uuid4(),
        channel=NotificationChannel.LOG,
        priority=NotificationPriority.HIGH,
        subject="Subject",
        message="Message",
        source_type="ALERT_CREATED",
        source_id="1",
        metadata={"event_type": "notifications.dispatch"},
    )

    result = await NotificationDispatcher().dispatch(event)

    assert result.status == NotificationStatus.DELIVERED
    assert result.delivered is True
    assert result.provider_message_id is not None
    assert result.metadata["delivery"]["adapter_name"] == LogNotificationAdapter.adapter_name
