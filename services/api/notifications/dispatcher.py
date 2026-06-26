from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from loguru import logger

from .base import (
    NotificationChannel,
    NotificationDeliveryResult,
    NotificationDispatchResult,
    NotificationEvent,
    NotificationPriority,
    NotificationStatus,
)
from .notification_policy import NotificationPolicyResult
from .notification_policy_service import NotificationPolicyService, notification_policy_service
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
        policy_service: NotificationPolicyService | None = None,
    ) -> None:
        self.registry = registry or notification_adapter_registry
        self.policy_service = policy_service or notification_policy_service

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
        bound_logger = self._logger(event)
        bound_logger.info("notification_dispatch_started")
        try:
            policy_result = self.policy_service.evaluate(event)
            if not policy_result.allowed:
                delivery = self._suppressed_delivery(event, policy_result)
                result = self._to_result(event, delivery, started_at, policy_result)
                adapter_name = delivery.metadata.get("adapter_name")
            else:
                deliveries = await self._deliver(event, policy_result)
                primary_delivery = self._primary_delivery(deliveries)
                result = self._to_result(
                    event,
                    primary_delivery,
                    started_at,
                    policy_result,
                    deliveries=deliveries,
                )
                adapter_name = primary_delivery.metadata.get("adapter_name")
        except NotificationAdapterNotRegisteredError as exc:
            delivery = self._not_implemented_delivery(event, str(exc))
            result = self._to_result(event, delivery, started_at, None)
            adapter_name = delivery.metadata.get("adapter_name")
        except Exception as exc:  # pragma: no cover - defensive isolation
            delivery = self._failed_delivery(event, exc)
            result = self._to_result(event, delivery, started_at, None)
            adapter_name = delivery.metadata.get("adapter_name")
            bound_logger.exception("notification_dispatch_failed")
        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(timezone.utc)  # noqa: UP017
        bound_logger.bind(
            event_type=event.metadata.get("event_type"),
            policy_allowed=(
                result.metadata.get("policy", {}).get("allowed")
                if isinstance(result.metadata.get("policy"), dict)
                else None
            ),
            policy_reason=(
                result.metadata.get("policy", {}).get("reason")
                if isinstance(result.metadata.get("policy"), dict)
                else None
            ),
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
        policy_result: NotificationPolicyResult | None,
        deliveries: list[NotificationDeliveryResult] | None = None,
    ) -> NotificationDispatchResult:
        resolved_deliveries = deliveries or [delivery]
        return NotificationDispatchResult(
            notification_id=event.notification_id,
            channel=delivery.channel,
            status=delivery.status,
            priority=delivery.priority or event.priority,
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
                "deliveries": [item.model_dump() for item in resolved_deliveries],
                "policy": (
                    policy_result.model_dump() if policy_result is not None else None
                ),
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

    def _suppressed_delivery(
        self,
        event: NotificationEvent,
        policy_result: NotificationPolicyResult,
    ) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=self._primary_channel(policy_result, event),
            status=NotificationStatus.SKIPPED,
            priority=self._priority_from(policy_result),
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            skipped=True,
            error=policy_result.reason,
            metadata={
                "adapter_name": "policy",
                "reason": policy_result.reason,
                "policy": policy_result.model_dump(),
            },
        )

    async def _deliver(
        self,
        event: NotificationEvent,
        policy_result: NotificationPolicyResult,
    ) -> list[NotificationDeliveryResult]:
        deliveries: list[NotificationDeliveryResult] = []
        for channel in self._normalize_channels(policy_result.channels, event):
            deliveries.append(
                await self._deliver_channel(event, policy_result, channel)
            )
        if deliveries:
            return deliveries
        return [self._suppressed_delivery(event, policy_result)]

    async def _deliver_channel(
        self,
        event: NotificationEvent,
        policy_result: NotificationPolicyResult,
        channel: NotificationChannel,
    ) -> NotificationDeliveryResult:
        try:
            adapter_cls = self.registry.resolve(channel)
            channel_event = self._channel_event(event, policy_result, channel)
            delivery = await adapter_cls().send(channel_event)
            return delivery.model_copy(
                update={
                    "priority": self._priority_from(policy_result),
                    "metadata": {
                        **delivery.metadata,
                        "policy": policy_result.model_dump(),
                    },
                }
            )
        except NotificationAdapterNotRegisteredError as exc:
            return self._not_implemented_delivery(event, str(exc))
        except Exception as exc:  # pragma: no cover - defensive isolation
            return self._failed_channel_delivery(
                event,
                policy_result,
                channel,
                exc,
            )

    @staticmethod
    def _normalize_channels(
        channels: list[str],
        event: NotificationEvent,
    ) -> list[NotificationChannel]:
        normalized: list[NotificationChannel] = []
        for channel in channels:
            normalized.append(NotificationChannel(str(channel).strip().upper()))
        if normalized:
            return normalized
        return [event.channel]

    @staticmethod
    def _primary_channel(
        policy_result: NotificationPolicyResult,
        event: NotificationEvent,
    ) -> NotificationChannel:
        channels = NotificationDispatcher._normalize_channels(policy_result.channels, event)
        return channels[0]

    @staticmethod
    def _primary_delivery(
        deliveries: list[NotificationDeliveryResult],
    ) -> NotificationDeliveryResult:
        for delivery in deliveries:
            if delivery.delivered and not delivery.failed:
                return delivery
        return deliveries[0]

    @staticmethod
    def _priority_from(policy_result: NotificationPolicyResult) -> NotificationPriority:
        return NotificationPriority[policy_result.priority.strip().upper()]

    def _channel_event(
        self,
        event: NotificationEvent,
        policy_result: NotificationPolicyResult,
        channel: NotificationChannel,
    ) -> NotificationEvent:
        return event.model_copy(
            update={
                "channel": channel,
                "priority": self._priority_from(policy_result),
                "metadata": {
                    **event.metadata,
                    "policy": policy_result.model_dump(),
                    "resolved_recipients": policy_result.recipients,
                    "resolved_channels": policy_result.channels,
                },
            }
        )

    def _failed_channel_delivery(
        self,
        event: NotificationEvent,
        policy_result: NotificationPolicyResult,
        channel: NotificationChannel,
        exc: Exception,
    ) -> NotificationDeliveryResult:
        logger.bind(
            component="notification_dispatcher",
            notification_id=str(event.notification_id),
            tenant_id=str(event.tenant_id),
            channel=channel.value,
            event_type=policy_result.event_type,
            exception_type=exc.__class__.__name__,
        ).exception("notification_channel_delivery_failed")
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=channel,
            status=NotificationStatus.FAILED,
            priority=self._priority_from(policy_result),
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            failed=True,
            error=f"{exc.__class__.__name__}: {exc}",
            metadata={
                "adapter_name": "policy",
                "exception_type": exc.__class__.__name__,
                "policy": policy_result.model_dump(),
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
