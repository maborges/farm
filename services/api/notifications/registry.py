from __future__ import annotations

from importlib import import_module

from .base import NotificationAdapter, NotificationChannel


class NotificationAdapterNotRegisteredError(LookupError):
    """Raised when a notification channel has no registered adapter."""

    def __init__(self, channel: NotificationChannel | str) -> None:
        self.channel = str(channel)
        super().__init__(f"No notification adapter registered for channel: {self.channel}")


class NotificationAdapterRegistry:
    """Explicit in-memory registry for notification adapters."""

    def __init__(self) -> None:
        self._adapters: dict[NotificationChannel, type[NotificationAdapter]] = {}
        self._default_adapters_loaded = False

    def register(self, adapter_cls: type[NotificationAdapter]) -> type[NotificationAdapter]:
        """Register an adapter for all declared channels."""

        channels = getattr(adapter_cls, "supported_channels", ())
        if not channels:
            raise ValueError(f"Adapter has no supported channels: {adapter_cls.__name__}")
        for channel in channels:
            self._adapters[NotificationChannel(channel)] = adapter_cls
        return adapter_cls

    def resolve(self, channel: NotificationChannel | str) -> type[NotificationAdapter]:
        """Return the adapter registered for a notification channel."""

        self._ensure_default_adapters_loaded()
        normalized = self._normalize_channel(channel)
        adapter = self._adapters.get(normalized)
        if adapter is None:
            raise NotificationAdapterNotRegisteredError(normalized)
        return adapter

    def list_supported_channels(self) -> tuple[NotificationChannel, ...]:
        """Return the channels currently supported by the registry."""

        self._ensure_default_adapters_loaded()
        return tuple(self._adapters.keys())

    @staticmethod
    def _normalize_channel(channel: NotificationChannel | str) -> NotificationChannel:
        if isinstance(channel, NotificationChannel):
            return channel
        return NotificationChannel(str(channel).strip().upper())

    def _ensure_default_adapters_loaded(self) -> None:
        if self is not notification_adapter_registry or self._default_adapters_loaded:
            return
        import_module("notifications.adapters")
        self._default_adapters_loaded = True


notification_adapter_registry = NotificationAdapterRegistry()


def register_notification_adapter(
    adapter_cls: type[NotificationAdapter],
) -> type[NotificationAdapter]:
    """Decorator that registers an adapter in the canonical registry."""

    return notification_adapter_registry.register(adapter_cls)
