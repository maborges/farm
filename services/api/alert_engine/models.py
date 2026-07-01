from __future__ import annotations

import uuid
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String, Text, Uuid as UUIDType, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Domain(str, Enum):
    AGRICULTURE = "AGRICULTURE"
    LIVESTOCK = "LIVESTOCK"
    FINANCE = "FINANCE"
    OPERATIONS = "OPERATIONS"
    FIELD = "FIELD"
    INTEGRATIONS = "INTEGRATIONS"
    SYSTEM = "SYSTEM"


class Category(str, Enum):
    SANITARIO = "SANITARIO"
    OPERACIONAL = "OPERACIONAL"
    ECONOMICO = "ECONOMICO"
    FINANCEIRO = "FINANCEIRO"
    CLIMATICO = "CLIMATICO"
    MANUTENCAO = "MANUTENCAO"
    GOVERNANCA = "GOVERNANCA"
    QUALIDADE = "QUALIDADE"
    COMPLIANCE = "COMPLIANCE"
    PRODUCAO = "PRODUCAO"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    SNOOZED = "SNOOZED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


ACTIVE_ALERT_STATUSES = (
    AlertStatus.OPEN.value,
    AlertStatus.ACKNOWLEDGED.value,
    AlertStatus.SNOOZED.value,
)


class TriggerType(str, Enum):
    RULE = "RULE"
    THRESHOLD = "THRESHOLD"
    MODEL = "MODEL"
    MANUAL = "MANUAL"
    SCHEDULE = "SCHEDULE"


class InsightGeneratedBy(str, Enum):
    RULE_ENGINE = "RULE_ENGINE"
    ANALYTICS = "ANALYTICS"
    COPILOT = "COPILOT"
    HUMAN = "HUMAN"


class LifecycleActionType(str, Enum):
    ACKNOWLEDGE = "ACKNOWLEDGE"
    SNOOZE = "SNOOZE"
    RESOLVE = "RESOLVE"
    DISMISS = "DISMISS"
    EXPIRE = "EXPIRE"
    REOPEN = "REOPEN"
    CREATE = "CREATE"


class AlertEvent(Base):
    """Append-only ledger of business facts consumed by the Alert Engine."""

    __tablename__ = "alert_events"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType(as_uuid=True), nullable=True)
    occurred_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType(as_uuid=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType(as_uuid=True), nullable=True)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("alert_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class AlertIndicator(Base):
    """Materialized or reusable derived metric consumed by the Alert Engine."""

    __tablename__ = "alert_indicators"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    period_start: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    computed_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    inputs: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    calculation_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class OperationalAlert(Base):
    """Current alert state and lifecycle fields."""

    __tablename__ = "operational_alerts"

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
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_event_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    source_indicator_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    action_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    action_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    lifecycle_events: Mapped[list["AlertLifecycleEvent"]] = relationship(
        "AlertLifecycleEvent",
        back_populates="alert",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AlertInsight(Base):
    """Narrative interpretation that can be persisted or generated on demand."""

    __tablename__ = "alert_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    evidence_event_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    evidence_indicator_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    evidence_alert_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(40), nullable=False)
    generated_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class AlertLifecycleEvent(Base):
    """Immutable audit trail for alert state changes."""

    __tablename__ = "alert_lifecycle_events"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("operational_alerts.id", ondelete="CASCADE"),
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

    alert: Mapped[OperationalAlert] = relationship("OperationalAlert", back_populates="lifecycle_events")
