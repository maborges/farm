from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class NotificationDeduplicationStore:
    """In-memory deduplication store scoped by tenant."""

    seen: dict[tuple[str, str], datetime] = field(default_factory=dict)

    def mark_if_new(self, tenant_id: UUID | str, dedupe_key: str) -> bool:
        """Register a dedupe key when it has not been seen yet."""

        key = (str(tenant_id), dedupe_key.strip())
        if key in self.seen:
            return False
        self.seen[key] = datetime.now().astimezone()
        return True
