from __future__ import annotations

from .notification_policy import DefaultNotificationPolicy, NotificationPolicy


class NotificationPolicyRegistry:
    """Explicit in-memory registry for notification policies."""

    def __init__(self) -> None:
        self._policies: dict[str, NotificationPolicy] = {}
        self._default_policy = DefaultNotificationPolicy()

    def register(self, policy: NotificationPolicy) -> NotificationPolicy:
        """Register a policy for its declared event type."""

        event_type = self._normalize_event_type(policy.event_type)
        self._policies[event_type] = policy
        return policy

    def get_policy(self, event_type: str) -> NotificationPolicy:
        """Return the most specific policy for the provided event type."""

        normalized = self._normalize_event_type(event_type)
        return (
            self._policies.get(normalized)
            or self._policies.get("*")
            or self._default_policy
        )

    def list_event_types(self) -> tuple[str, ...]:
        """Return the currently registered event types."""

        return tuple(self._policies.keys())

    @staticmethod
    def _normalize_event_type(event_type: str) -> str:
        normalized = str(event_type).strip()
        return normalized or "*"


notification_policy_registry = NotificationPolicyRegistry()


def register_notification_policy(policy: NotificationPolicy) -> NotificationPolicy:
    """Decorator helper for policy registration."""

    return notification_policy_registry.register(policy)
