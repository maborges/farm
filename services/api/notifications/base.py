from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar, Final
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

UTC: Final = timezone.utc  # noqa: UP017


class NotificationChannel(str, Enum):
    LOG = "LOG"
    NOOP = "NOOP"
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"


class NotificationPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationStatus(str, Enum):
    DELIVERED = "delivered"
    SKIPPED = "skipped"
    FAILED = "failed"
    NOT_IMPLEMENTED = "not_implemented"


class NotificationEvent(BaseModel):
    """Canonical envelope for a notification delivery attempt."""

    notification_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    recipient_user_id: UUID | None = None
    recipient_email: str | None = None
    recipient_phone: str | None = None
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.NORMAL
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)
    source_type: str = Field(min_length=1, max_length=120)
    source_id: str = Field(min_length=1, max_length=120)
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class NotificationDeliveryResult(BaseModel):
    """Canonical result returned by a notification adapter."""

    notification_id: UUID
    channel: NotificationChannel
    status: NotificationStatus
    priority: NotificationPriority | None = None
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    delivered: bool = False
    skipped: bool = False
    failed: bool = False
    error: str | None = None
    duration_ms: int = 0
    provider_message_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class NotificationDispatchResult(BaseModel):
    """Canonical aggregate returned by the dispatcher."""

    notification_id: UUID
    channel: NotificationChannel
    status: NotificationStatus
    priority: NotificationPriority | None = None
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    delivered: bool = False
    skipped: bool = False
    failed: bool = False
    error: str | None = None
    duration_ms: int = 0
    provider_message_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    delivery: NotificationDeliveryResult | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class NotificationAdapter(ABC):
    """Official contract for notification delivery adapters."""

    adapter_name: ClassVar[str] = "base"
    supported_channels: ClassVar[tuple[NotificationChannel, ...]] = ()

    @abstractmethod
    async def send(self, event: NotificationEvent) -> NotificationDeliveryResult:
        """Deliver a canonical notification event."""
