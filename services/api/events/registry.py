from __future__ import annotations

from importlib import import_module

from .base import EventSubscriber


class EventSubscriberRegistry:
    """Explicit in-memory registry for domain event subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[type[EventSubscriber]]] = {}
        self._default_subscribers_loaded = False

    def register(self, subscriber_cls: type[EventSubscriber]) -> type[EventSubscriber]:
        """Register a subscriber by its declared event types."""

        event_types = self._normalize_event_types(subscriber_cls)
        if not event_types:
            raise ValueError(f"Subscriber has no event types: {subscriber_cls.__name__}")
        for event_type in event_types:
            self._subscribers.setdefault(event_type, []).append(subscriber_cls)
        return subscriber_cls

    def list_subscribers(self) -> tuple[type[EventSubscriber], ...]:
        """Return all subscribers in registration order."""

        self._ensure_default_subscribers_loaded()
        ordered: list[type[EventSubscriber]] = []
        seen: set[type[EventSubscriber]] = set()
        for subscribers in self._subscribers.values():
            for subscriber_cls in subscribers:
                if subscriber_cls in seen:
                    continue
                seen.add(subscriber_cls)
                ordered.append(subscriber_cls)
        return tuple(ordered)

    def find_by_event_type(self, event_type: str) -> tuple[type[EventSubscriber], ...]:
        """Return subscribers mapped to the provided event type."""

        self._ensure_default_subscribers_loaded()
        return tuple(self._subscribers.get(self._normalize_event_type_value(event_type), ()))

    @staticmethod
    def _normalize_event_types(subscriber_cls: type[EventSubscriber]) -> tuple[str, ...]:
        values = getattr(subscriber_cls, "event_types", ())
        return tuple(
            normalized
            for normalized in (
                EventSubscriberRegistry._normalize_event_type_value(str(value)) for value in values
            )
            if normalized
        )

    @staticmethod
    def _normalize_event_type_value(event_type: str) -> str:
        return event_type.strip().lower()

    def _ensure_default_subscribers_loaded(self) -> None:
        if self is not event_subscriber_registry or self._default_subscribers_loaded:
            return
        import_module("events.subscribers")
        self._default_subscribers_loaded = True


event_subscriber_registry = EventSubscriberRegistry()


def register_event_subscriber(subscriber_cls: type[EventSubscriber]) -> type[EventSubscriber]:
    """Decorator that registers a subscriber in the canonical registry."""

    return event_subscriber_registry.register(subscriber_cls)
