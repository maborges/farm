from __future__ import annotations

from time import perf_counter

from loguru import logger

from .base import (
    NotificationAdapter,
    NotificationChannel,
    NotificationDeliveryResult,
    NotificationEvent,
    NotificationStatus,
)
from .registry import register_notification_adapter


@register_notification_adapter
class LogNotificationAdapter(NotificationAdapter):
    """Adapter that records delivery attempts to structured logs."""

    adapter_name = "log"
    supported_channels = (NotificationChannel.LOG,)

    async def send(self, event: NotificationEvent) -> NotificationDeliveryResult:
        """Log a notification event and mark it as delivered.

        Args:
            event: Canonical notification envelope.

        Returns:
            Delivery result indicating a successful log-only delivery.

        Raises:
            None.
        """

        start = perf_counter()
        logger.bind(
            component="notification_log_adapter",
            notification_id=str(event.notification_id),
            tenant_id=str(event.tenant_id),
            event_type=event.metadata.get("event_type"),
            unidade_produtiva_id=(
                str(event.unidade_produtiva_id) if event.unidade_produtiva_id else None
            ),
            recipient_user_id=(
                str(event.recipient_user_id) if event.recipient_user_id else None
            ),
            channel=event.channel.value,
            adapter=self.adapter_name,
            priority=event.priority.value,
            source_type=event.source_type,
            source_id=event.source_id,
            correlation_id=str(event.correlation_id) if event.correlation_id else None,
            causation_id=str(event.causation_id) if event.causation_id else None,
        ).info("notification_log_adapter_sent")
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=event.channel,
            status=NotificationStatus.DELIVERED,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            delivered=True,
            duration_ms=int((perf_counter() - start) * 1000),
            provider_message_id=f"log:{event.notification_id}",
            metadata={
                "adapter_name": self.adapter_name,
                "event_type": event.metadata.get("event_type"),
                "priority": event.priority.value,
            },
        )


@register_notification_adapter
class NoopNotificationAdapter(NotificationAdapter):
    """Adapter that records channels intentionally left unimplemented."""

    adapter_name = "noop"
    supported_channels = (
        NotificationChannel.NOOP,
        NotificationChannel.IN_APP,
        NotificationChannel.EMAIL,
        NotificationChannel.WHATSAPP,
        NotificationChannel.PUSH,
    )

    async def send(self, event: NotificationEvent) -> NotificationDeliveryResult:
        """Return a controlled not-implemented result for non-log channels."""

        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=event.channel,
            status=NotificationStatus.NOT_IMPLEMENTED,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            skipped=True,
            error=f"channel {event.channel.value} is not implemented",
            metadata={
                "adapter_name": self.adapter_name,
                "event_type": event.metadata.get("event_type"),
                "priority": event.priority.value,
            },
        )
