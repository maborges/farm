from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from loguru import logger

from .base import (
    NotificationDeliveryResult,
    NotificationDispatchResult,
    NotificationEvent,
    NotificationStatus,
)
from .registry import (
    NotificationAdapterNotRegisteredError,
    NotificationAdapterRegistry,
    notification_adapter_registry,
)


class NotificationDispatcher:
    """In-memory coordinator for notification delivery adapters."""

    def __init__(
        self,
        registry: NotificationAdapterRegistry | None = None,
    ) -> None:
        self.registry = registry or notification_adapter_registry

    async def dispatch(self, event: NotificationEvent) -> NotificationDispatchResult:
        """Dispatch a canonical notification event through the selected adapter.

        Args:
            event: Canonical notification envelope.

        Returns:
            Consolidated dispatch result with delivery outcome details.

        Raises:
            None.
        """

        started_at = datetime.now(timezone.utc)  # noqa: UP017
        start = perf_counter()
        adapter_name: str | None = None
        bound_logger = self._logger(event)
        bound_logger.info("notification_dispatch_started")
        try:
            adapter_cls = self.registry.resolve(event.channel)
            delivery = await adapter_cls().send(event)
            adapter_name = delivery.metadata.get("adapter_name")
            result = self._to_result(event, delivery, started_at)
        except NotificationAdapterNotRegisteredError as exc:
            delivery = self._not_implemented_delivery(event, str(exc))
            result = self._to_result(event, delivery, started_at)
            adapter_name = delivery.metadata.get("adapter_name")
        except Exception as exc:  # pragma: no cover - defensive isolation
            delivery = self._failed_delivery(event, exc)
            result = self._to_result(event, delivery, started_at)
            adapter_name = delivery.metadata.get("adapter_name")
            bound_logger.exception("notification_dispatch_failed")
        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(timezone.utc)  # noqa: UP017
        bound_logger.bind(
            event_type=event.metadata.get("event_type"),
            adapter=adapter_name,
            status=result.status.value,
            duration_ms=result.duration_ms,
            delivered=result.delivered,
            skipped=result.skipped,
            failed=result.failed,
            error=result.error,
        ).info("notification_dispatch_finished")
        return result

    @staticmethod
    def _to_result(
        event: NotificationEvent,
        delivery: NotificationDeliveryResult,
        started_at: datetime,
    ) -> NotificationDispatchResult:
        return NotificationDispatchResult(
            notification_id=event.notification_id,
            channel=event.channel,
            status=delivery.status,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            delivered=delivery.delivered,
            skipped=delivery.skipped,
            failed=delivery.failed,
            error=delivery.error,
            provider_message_id=delivery.provider_message_id,
            metadata={
                **event.metadata,
                "delivery": delivery.metadata,
            },
            started_at=started_at,
            delivery=delivery,
        )

    @staticmethod
    def _not_implemented_delivery(
        event: NotificationEvent,
        error: str,
    ) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=event.channel,
            status=NotificationStatus.NOT_IMPLEMENTED,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            skipped=True,
            error=error,
            metadata={"reason": "channel_not_registered"},
        )

    @staticmethod
    def _failed_delivery(
        event: NotificationEvent,
        exc: Exception,
    ) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=event.channel,
            status=NotificationStatus.FAILED,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            failed=True,
            error=f"{exc.__class__.__name__}: {exc}",
            metadata={
                "exception_type": exc.__class__.__name__,
            },
        )

    @staticmethod
    def _logger(event: NotificationEvent) -> Any:
        return logger.bind(
            component="notification_dispatcher",
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
            priority=event.priority.value,
            source_type=event.source_type,
            source_id=event.source_id,
            correlation_id=str(event.correlation_id) if event.correlation_id else None,
            causation_id=str(event.causation_id) if event.causation_id else None,
        )
