from __future__ import annotations

from dataclasses import dataclass, field

from .base import NotificationEvent, NotificationPriority
from .notification_deduplication import NotificationDeduplicationStore
from .notification_policy import NotificationPolicyResult
from .notification_policy_registry import (
    NotificationPolicyRegistry,
    notification_policy_registry,
)
from .notification_preferences import NotificationPreferences
from .notification_silence_window import NotificationSilenceWindow


@dataclass(slots=True)
class NotificationPolicyService:
    """Orchestrate policy lookup, dedupe, and silence-window checks."""

    registry: NotificationPolicyRegistry = notification_policy_registry
    deduplication_store: NotificationDeduplicationStore = field(
        default_factory=NotificationDeduplicationStore
    )
    silence_window: NotificationSilenceWindow = field(
        default_factory=NotificationSilenceWindow
    )

    def evaluate(self, event: NotificationEvent) -> NotificationPolicyResult:
        """Evaluate policy, dedupe, and silence-window rules for an event."""

        policy = self.registry.get_policy(self._event_type(event))
        preferences = self._preferences(event)
        result = policy.evaluate(event, preferences)
        if not result.allowed:
            return result
        if self._is_duplicate(event, result.dedupe_key):
            return self._block(
                result,
                "duplicate_notification_suppressed",
                silence_window_applied=False,
            )
        if self._is_silenced(result.priority):
            return self._block(
                result,
                "silence_window_suppressed",
                silence_window_applied=True,
            )
        return result

    def _is_duplicate(self, event: NotificationEvent, dedupe_key: str | None) -> bool:
        if not dedupe_key:
            return False
        return not self.deduplication_store.mark_if_new(event.tenant_id, dedupe_key)

    def _is_silenced(self, priority: str) -> bool:
        normalized = NotificationPriority[str(priority).strip().upper()]
        return self.silence_window.should_suppress(normalized)

    def _block(
        self,
        result: NotificationPolicyResult,
        reason: str,
        *,
        silence_window_applied: bool,
    ) -> NotificationPolicyResult:
        return result.model_copy(
            update={
                "allowed": False,
                "reason": reason,
                "silence_window_applied": silence_window_applied,
            }
        )

    def _event_type(self, event: NotificationEvent) -> str:
        event_type = event.metadata.get("event_type", event.source_type)
        return str(event_type).strip() or event.source_type

    def _preferences(self, event: NotificationEvent) -> NotificationPreferences | None:
        raw_preferences = event.metadata.get("notification_preferences")
        if not isinstance(raw_preferences, dict):
            return None
        return NotificationPreferences.from_mapping(raw_preferences)


notification_policy_service = NotificationPolicyService()
