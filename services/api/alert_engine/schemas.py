from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from alert_engine.models import (
    AlertStatus,
    Category,
    Domain,
    InsightGeneratedBy,
    LifecycleActionType,
    Priority,
    Severity,
    TriggerType,
)


class AlertEventBase(BaseModel):
    tenant_id: UUID
    domain: Domain
    category: Category
    source: str = Field(min_length=1, max_length=120)
    source_id: UUID | None = None
    occurred_at: datetime
    ingested_at: datetime
    actor_id: UUID | None = None
    entity_type: str | None = Field(default=None, max_length=80)
    entity_id: UUID | None = None
    payload: dict[str, Any]
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class AlertEventCreate(AlertEventBase):
    @model_validator(mode="after")
    def _ensure_payload_not_empty(self) -> "AlertEventCreate":
        if not self.payload:
            raise ValueError("payload must not be empty")
        return self


class AlertEventResponse(AlertEventBase):
    id: UUID
    created_at: datetime
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AlertIndicatorBase(BaseModel):
    tenant_id: UUID
    domain: Domain
    category: Category
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    value_numeric: Decimal | None = None
    value_text: str | None = None
    value_bool: bool | None = None
    unit: str | None = Field(default=None, max_length=40)
    period_start: datetime | None = None
    period_end: datetime | None = None
    computed_at: datetime
    inputs: list[str]
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] | None = None
    calculation_version: str = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def _ensure_single_value(self) -> "AlertIndicatorBase":
        values_set = sum(
            1 for value in (self.value_numeric, self.value_text, self.value_bool) if value is not None
        )
        if values_set > 1:
            raise ValueError("only one indicator value field may be populated")
        return self


class AlertIndicatorCreate(AlertIndicatorBase):
    pass


class AlertIndicatorResponse(AlertIndicatorBase):
    id: UUID
    created_at: datetime
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OperationalAlertBase(BaseModel):
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: Domain
    category: Category
    title: str = Field(min_length=1, max_length=180)
    message: str
    severity: Severity
    priority: Priority
    status: AlertStatus
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    trigger_type: TriggerType
    source_type: str = Field(min_length=1, max_length=120)
    source_id: str = Field(min_length=1, max_length=120)
    source_event_ids: list[UUID]
    source_indicator_ids: list[UUID]
    dedupe_key: str = Field(min_length=1, max_length=160)
    action_label: str | None = Field(default=None, max_length=120)
    action_url: str | None = None
    context: dict[str, Any] | None = None
    expires_at: datetime | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    acknowledged_by: UUID | None = None
    resolved_by: UUID | None = None


class OperationalAlertCreate(OperationalAlertBase):
    pass


class OperationalAlertStatusUpdate(BaseModel):
    status: AlertStatus


class OperationalAlertResponse(OperationalAlertBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AlertInsightBase(BaseModel):
    tenant_id: UUID
    domain: Domain
    category: Category
    title: str = Field(min_length=1, max_length=180)
    summary: str
    narrative: str
    severity: Severity | None = None
    priority: Priority | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    evidence_event_ids: list[UUID]
    evidence_indicator_ids: list[UUID]
    evidence_alert_ids: list[UUID]
    generated_by: InsightGeneratedBy
    generated_at: datetime
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class AlertInsightCreate(AlertInsightBase):
    pass


class AlertInsightResponse(AlertInsightBase):
    id: UUID
    created_at: datetime
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AlertLifecycleEventBase(BaseModel):
    tenant_id: UUID
    alert_id: UUID
    actor_id: UUID | None = None
    action_type: LifecycleActionType
    previous_status: AlertStatus
    new_status: AlertStatus
    payload: dict[str, Any] | None = None
    source_channel: str = Field(min_length=1, max_length=40)


class AlertLifecycleEventCreate(AlertLifecycleEventBase):
    pass


class AlertLifecycleEventResponse(AlertLifecycleEventBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertQueryParams(BaseModel):
    domain: Domain | None = None
    category: Category | None = None
    severity: Severity | None = None
    priority: Priority | None = None
    status: AlertStatus | None = None
    source_type: str | None = None
    source_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class AlertQueryResponse(BaseModel):
    alerts: list[OperationalAlertResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    items: list[OperationalAlertResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class AlertSummaryByDomain(BaseModel):
    open: int = Field(ge=0)
    critical: int = Field(ge=0)
    urgent: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class AlertSummary(BaseModel):
    total_open: int = Field(ge=0)
    max_severity: Severity | None = None
    max_priority: Priority | None = None
    most_critical_domain: Domain | None = None
    by_domain: dict[str, AlertSummaryByDomain]
    top_alerts: list[OperationalAlertResponse]

    model_config = ConfigDict(from_attributes=True)
