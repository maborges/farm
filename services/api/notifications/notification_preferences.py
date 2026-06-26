from __future__ import annotations

from dataclasses import dataclass, field

from .base import NotificationPriority


@dataclass(slots=True, frozen=True)
class NotificationPreferences:
    """In-memory policy preferences for notification delivery."""

    preferred_channels: tuple[str, ...] = ("LOG",)
    recipients: tuple[str, ...] = ()
    priority: NotificationPriority | None = None
    dedupe_key: str | None = None
    suppressed_event_types: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_mapping(cls, mapping: dict[str, object]) -> NotificationPreferences:
        """Build a preference object from a raw metadata mapping."""

        channels_source = mapping.get("preferred_channels")
        recipients_source = mapping.get("recipients")
        suppressed_source = mapping.get("suppressed_event_types")
        channels = tuple(
            str(value).strip().upper()
            for value in (
                channels_source
                if isinstance(channels_source, list | tuple | set)
                else ["LOG"]
            )
        )
        recipients = tuple(
            str(value).strip()
            for value in (
                recipients_source
                if isinstance(recipients_source, list | tuple | set)
                else []
            )
        )
        priority = mapping.get("priority")
        normalized_priority = (
            NotificationPriority[str(priority).strip().upper()]
            if priority is not None
            else None
        )
        dedupe_key = mapping.get("dedupe_key")
        suppressed_event_types = frozenset(
            str(value).strip()
            for value in (
                suppressed_source
                if isinstance(suppressed_source, list | tuple | set)
                else []
            )
        )
        return cls(
            preferred_channels=channels,
            recipients=recipients,
            priority=normalized_priority,
            dedupe_key=str(dedupe_key).strip() if dedupe_key else None,
            suppressed_event_types=suppressed_event_types,
        )
