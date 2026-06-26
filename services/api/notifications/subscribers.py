from __future__ import annotations

from typing import Any

from .base import NotificationEvent, NotificationPriority
from .dispatcher import NotificationDispatcher


class NotificationEventSubscriber:
    """Optional future bridge from domain events to the notification dispatcher."""

    subscriber_name = "notification-dispatcher"
    event_types = ("notifications.dispatch",)

    def __init__(
        self,
        session: Any | None = None,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        self.session = session
        self.dispatcher = (
            dispatcher or (NotificationDispatcher() if session is not None else None)
        )

    async def handle(self, event: Any) -> Any:
        """Handle a domain event using a future-safe, lazy import path."""

        from events.base import EventSubscriberResult

        if self.dispatcher is None:
            return EventSubscriberResult(
                event_id=event.event_id,
                event_type=event.event_type,
                subscriber_name=self.subscriber_name,
                status="skipped",
                skipped=1,
                metadata={
                    "reason": "notification_event_subscriber_not_wired",
                    "event_type": event.event_type,
                },
            )

        notification_event = self._to_notification_event(event)
        result = await self.dispatcher.dispatch(notification_event)
        subscriber_status = (
            "failed" if result.failed else "skipped" if result.skipped else "success"
        )
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name=self.subscriber_name,
            status=subscriber_status,
            skipped=1 if result.skipped else 0,
            errors=1 if result.failed else 0,
            metadata={
                "notification_id": str(result.notification_id),
                "channel": result.channel.value,
                "status": result.status.value,
            },
        )

    @staticmethod
    def _to_notification_event(event: Any) -> NotificationEvent:
        metadata = dict(event.metadata)
        metadata.setdefault("event_type", event.event_type)
        metadata.setdefault("event_id", str(event.event_id))
        metadata.setdefault(
            "domain",
            event.domain.value if hasattr(event.domain, "value") else str(event.domain),
        )
        return NotificationEvent(
            tenant_id=event.tenant_id,
            unidade_produtiva_id=event.unidade_produtiva_id,
            recipient_user_id=metadata.get("recipient_user_id"),
            recipient_email=metadata.get("recipient_email"),
            recipient_phone=metadata.get("recipient_phone"),
            channel=metadata.get("channel", "LOG"),
            priority=NotificationPriority.NORMAL,
            subject=metadata.get("subject", event.event_type),
            message=metadata.get("message", event.source_type),
            source_type=event.source_type,
            source_id=str(event.entity_id or event.event_id),
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            metadata=metadata,
        )
