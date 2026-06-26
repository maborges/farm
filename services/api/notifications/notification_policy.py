from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .base import NotificationEvent, NotificationPriority
from .notification_preferences import NotificationPreferences


class NotificationPolicyResult(BaseModel):
    """Canonical result produced by notification policy evaluation."""

    allowed: bool
    reason: str | None = None
    tenant_id: UUID | str
    event_type: str
    priority: str
    channels: list[str] = Field(default_factory=list)
    recipients: list[str] = Field(default_factory=list)
    dedupe_key: str | None = None
    silence_window_applied: bool = False

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class NotificationPolicy:
    """Base contract for policy-driven notification evaluation."""

    policy_name: ClassVar[str] = "base"
    event_type: ClassVar[str] = "*"

    def evaluate(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> NotificationPolicyResult:
        """Evaluate the event and resolve delivery intent."""

        event_type = self.resolve_event_type(event)
        return NotificationPolicyResult(
            allowed=True,
            tenant_id=event.tenant_id,
            event_type=event_type,
            priority=self.resolve_priority(event, preferences).value,
            channels=self.resolve_channels(event, preferences),
            recipients=self.resolve_recipients(event, preferences),
            dedupe_key=self.resolve_dedupe_key(event, preferences),
        )

    def resolve_event_type(self, event: NotificationEvent) -> str:
        """Resolve the effective event type used for policy lookup."""

        raw_event_type = event.metadata.get("event_type", event.source_type)
        return str(raw_event_type).strip() or event.source_type

    def resolve_priority(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> NotificationPriority:
        """Resolve the priority used by the notification workflow."""

        if preferences and preferences.priority is not None:
            return preferences.priority
        return event.priority

    def resolve_channels(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> list[str]:
        """Resolve the channels that may receive the notification."""

        if preferences and preferences.preferred_channels:
            return list(preferences.preferred_channels)
        return [event.channel.value]

    def resolve_recipients(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> list[str]:
        """Resolve the recipients authorized for the notification."""

        if preferences and preferences.recipients:
            return list(preferences.recipients)
        recipients: list[str] = []
        for value in (event.recipient_email, event.recipient_phone):
            if value:
                recipients.append(value)
        if event.recipient_user_id:
            recipients.append(str(event.recipient_user_id))
        return recipients

    def resolve_dedupe_key(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> str | None:
        """Resolve the deduplication key for the current event."""

        if preferences and preferences.dedupe_key:
            return preferences.dedupe_key
        return self._default_dedupe_key(event)

    def _default_dedupe_key(self, event: NotificationEvent) -> str | None:
        payload = [
            self.resolve_event_type(event),
            event.source_type,
            event.source_id,
            event.channel.value,
        ]
        if not any(payload):
            return None
        return ":".join(str(item) for item in payload if str(item).strip())


class DefaultNotificationPolicy(NotificationPolicy):
    """Safe default policy used when no explicit rule is registered."""

    policy_name = "default"
    event_type = "*"

    def resolve_priority(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> NotificationPriority:
        """Force the default priority to NORMAL for safety."""

        return NotificationPriority.NORMAL

    def resolve_channels(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> list[str]:
        """Route all fallback notifications to LOG."""

        return ["LOG"]

    def resolve_recipients(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> list[str]:
        """Avoid recipient fan-out for the safe fallback policy."""

        return []

    def resolve_dedupe_key(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> str | None:
        """Disable persistent deduplication in the fallback policy."""

        return None
