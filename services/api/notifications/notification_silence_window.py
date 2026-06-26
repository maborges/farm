from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final

from .base import NotificationPriority

UTC: Final = timezone.utc  # noqa: UP017


@dataclass(slots=True)
class NotificationSilenceWindow:
    """Configurable quiet-hours window evaluated in memory."""

    quiet_start_hour: int = 22
    quiet_end_hour: int = 6
    allow_high_priority: bool = True
    clock: Callable[[], datetime] = field(
        default=lambda: datetime.now(UTC),
        repr=False,
    )

    def should_suppress(self, priority: NotificationPriority) -> bool:
        """Return whether the current time falls inside the quiet window."""

        if self.allow_high_priority and priority in (
            NotificationPriority.HIGH,
            NotificationPriority.CRITICAL,
        ):
            return False
        return self._is_quiet_now()

    def _is_quiet_now(self) -> bool:
        current_hour = self.clock().hour
        if self.quiet_start_hour == self.quiet_end_hour:
            return True
        if self.quiet_start_hour < self.quiet_end_hour:
            return self.quiet_start_hour <= current_hour < self.quiet_end_hour
        return current_hour >= self.quiet_start_hour or current_hour < self.quiet_end_hour
