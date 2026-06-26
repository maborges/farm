from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession


class DomainEvent(BaseModel):  # type: ignore[misc]
    """Canonical in-memory domain event envelope."""

    event_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: Any
    event_type: str = Field(min_length=1, max_length=120)
    source_type: str = Field(min_length=1, max_length=120)
    entity_type: str | None = Field(default=None, max_length=80)
    entity_id: UUID | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # noqa: UP017
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class EventSubscriber(ABC):
    """Official contract for in-memory domain event subscribers."""

    subscriber_name: ClassVar[str] = "base"
    event_types: ClassVar[tuple[str, ...]] = ()

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    @abstractmethod
    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        """Handle a domain event and return a canonical subscriber result."""


class EventSubscriberResult(BaseModel):  # type: ignore[misc]
    """Canonical result returned by a subscriber execution."""

    event_id: UUID
    event_type: str
    subscriber_name: str
    status: str
    created: int = 0
    updated: int = 0
    ignored: int = 0
    skipped: int = 0
    warnings: int = 0
    errors: int = 0
    duration_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)
