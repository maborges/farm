from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, cast

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Uuid as UUIDType,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base

from .base import DomainEvent

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    UTC = timezone.utc  # noqa: UP017


class DomainEventOutboxStatus(str, Enum):
    """Canonical lifecycle states for outbox rows."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class DomainEventOutbox(Base):  # type: ignore[misc]
    """Persisted outbox row for a canonical domain event."""

    __tablename__ = "domain_event_outbox"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType(as_uuid=True), nullable=True)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DomainEventOutboxStatus.PENDING.value,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_domain_event_outbox_tenant_idempotency_key",
        ),
        Index("ix_domain_event_outbox_tenant_status", "tenant_id", "status"),
        Index("ix_domain_event_outbox_status_next_attempt_at", "status", "next_attempt_at"),
    )

    @classmethod
    def from_domain_event(
        cls,
        event: DomainEvent,
        idempotency_key: str,
    ) -> DomainEventOutbox:
        """Build an outbox row from a canonical domain event."""

        return cls(
            tenant_id=event.tenant_id,
            unidade_produtiva_id=event.unidade_produtiva_id,
            event_type=event.event_type,
            source_type=event.source_type,
            source_id=str(event.entity_id or event.event_id),
            payload=event.model_dump(mode="json"),
            metadata_=dict(event.metadata),
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            status=DomainEventOutboxStatus.PENDING.value,
            attempts=0,
            next_attempt_at=datetime.now(UTC),
            idempotency_key=idempotency_key,
        )

    def to_domain_event(self) -> DomainEvent:
        """Rebuild the canonical domain event from the persisted payload."""

        return cast(DomainEvent, DomainEvent.model_validate(self.payload))
