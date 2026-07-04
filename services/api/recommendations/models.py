from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, Uuid as UUIDType, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class RecommendationResult(Base):
    """Current recommendation state stored by the global engine."""

    __tablename__ = "recommendation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("unidades_produtivas.id", ondelete="SET NULL"),
        nullable=True,
    )
    domain: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(120), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_signal_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    action_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    action_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    viewed_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    postponed_until: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("recommendation_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    lifecycle_events: Mapped[list["RecommendationLifecycleEvent"]] = relationship(
        "RecommendationLifecycleEvent",
        back_populates="recommendation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RecommendationLifecycleEvent(Base):
    """Immutable audit trail for recommendation lifecycle changes."""

    __tablename__ = "recommendation_lifecycle_events"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("recommendation_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    recommendation: Mapped[RecommendationResult] = relationship(
        "RecommendationResult",
        back_populates="lifecycle_events",
    )
