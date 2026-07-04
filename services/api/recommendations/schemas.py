from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    RecommendationActionType,
    RecommendationDomain,
    RecommendationLifecycleActionType,
    RecommendationPriority,
    RecommendationSourceType,
    RecommendationStatus,
)


class RecommendationSignal(BaseModel):
    signal_id: UUID
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: RecommendationDomain
    source_type: RecommendationSourceType
    key: str = Field(min_length=1, max_length=120)
    entity_type: str | None = Field(default=None, max_length=80)
    entity_id: UUID | None = None
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class OperationalContext(BaseModel):
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: RecommendationDomain
    scope_type: str = Field(min_length=1, max_length=80)
    scope_id: str = Field(min_length=1, max_length=120)
    source_signal_ids: list[UUID] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RecommendationCandidate(BaseModel):
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: RecommendationDomain
    priority: RecommendationPriority
    source_type: RecommendationSourceType
    action_type: RecommendationActionType
    provider_name: str = Field(min_length=1, max_length=120)
    rule_code: str = Field(min_length=1, max_length=120)
    scope_type: str = Field(min_length=1, max_length=80)
    scope_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=180)
    summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    dedupe_key: str = Field(min_length=1, max_length=160)
    source_signal_ids: list[UUID] = Field(default_factory=list)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    action_label: str | None = Field(default=None, max_length=120)
    action_target: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_action_target(self) -> "RecommendationCandidate":
        if self.action_type != RecommendationActionType.NONE and not self.action_target:
            raise ValueError("action_target is required when action_type is not NONE")
        return self


class RecommendationResultBase(BaseModel):
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: RecommendationDomain
    status: RecommendationStatus
    priority: RecommendationPriority
    source_type: RecommendationSourceType
    action_type: RecommendationActionType
    provider_name: str = Field(min_length=1, max_length=120)
    rule_code: str = Field(min_length=1, max_length=120)
    scope_type: str = Field(min_length=1, max_length=80)
    scope_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=180)
    summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    dedupe_key: str = Field(min_length=1, max_length=160)
    source_signal_ids: list[UUID]
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    action_label: str | None = Field(default=None, max_length=120)
    action_target: str | None = None
    context: dict[str, Any] | None = None
    expires_at: datetime | None = None
    viewed_at: datetime | None = None
    accepted_at: datetime | None = None
    dismissed_at: datetime | None = None
    postponed_until: datetime | None = None
    executed_at: datetime | None = None
    expired_at: datetime | None = None
    superseded_at: datetime | None = None
    superseded_by_id: UUID | None = None


class RecommendationResultCreate(RecommendationResultBase):
    pass


class RecommendationResultResponse(RecommendationResultBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RecommendationDismissRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RecommendationPostponeRequest(BaseModel):
    until: datetime
    reason: str | None = Field(default=None, max_length=500)


class RecommendationExecuteRequest(BaseModel):
    execution_note: str | None = Field(default=None, max_length=500)


class RecommendationLifecycleEventCreate(BaseModel):
    tenant_id: UUID
    recommendation_id: UUID
    actor_id: UUID | None = None
    action_type: RecommendationLifecycleActionType
    previous_status: RecommendationStatus
    new_status: RecommendationStatus
    payload: dict[str, Any] | None = None
    source_channel: str = Field(min_length=1, max_length=40)


class RecommendationLifecycleEventResponse(RecommendationLifecycleEventCreate):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationMetricsFilterResponse(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    domain: RecommendationDomain | None = None
    unidade_produtiva_id: UUID | None = None


class RecommendationMetricsTimelinePointResponse(BaseModel):
    period: date
    total_recommendations: int = 0
    viewed_total: int = 0
    accepted_total: int = 0
    dismissed_total: int = 0
    executed_total: int = 0
    accept_rate: float = 0.0
    dismissed_rate: float = 0.0
    executed_rate: float = 0.0


class RecommendationMetricsSummaryResponse(BaseModel):
    filters: RecommendationMetricsFilterResponse
    generated_at: datetime
    tenant_id: UUID
    total_recommendations: int
    by_domain: dict[str, int]
    by_status: dict[str, int]
    by_priority: dict[str, int]
    viewed_total: int
    accepted_total: int
    dismissed_total: int
    executed_total: int
    expired_total: int
    superseded_total: int
    reopened_total: int
    view_rate: float
    accept_rate: float
    dismiss_rate: float
    execute_rate: float
    avg_time_to_view_seconds: float | None
    avg_time_to_accept_seconds: float | None
    avg_time_to_execute_seconds: float | None
    lifecycle_events_total: int
    timeline: list[RecommendationMetricsTimelinePointResponse]


class RecommendationDomainMetricsResponse(BaseModel):
    domain: RecommendationDomain
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    viewed_total: int
    accepted_total: int
    dismissed_total: int
    executed_total: int
    view_rate: float
    accept_rate: float
    dismiss_rate: float
    execute_rate: float
    avg_time_to_view_seconds: float | None
    avg_time_to_accept_seconds: float | None
    avg_time_to_execute_seconds: float | None


class RecommendationDomainMetricsListResponse(BaseModel):
    filters: RecommendationMetricsFilterResponse
    generated_at: datetime
    items: list[RecommendationDomainMetricsResponse]


class RecommendationRuleMetricsItem(BaseModel):
    rule_code: str
    provider_name: str
    domain: RecommendationDomain
    total: int
    accepted_total: int
    dismissed_total: int
    executed_total: int
    view_rate: float
    accept_rate: float
    dismiss_rate: float
    execute_rate: float


class RecommendationRuleMetricsResponse(BaseModel):
    filters: RecommendationMetricsFilterResponse
    generated_at: datetime
    top_by_volume: list[RecommendationRuleMetricsItem]
    top_by_acceptance: list[RecommendationRuleMetricsItem]
    top_by_dismissal: list[RecommendationRuleMetricsItem]


class RecommendationLifecycleMetricsResponse(BaseModel):
    filters: RecommendationMetricsFilterResponse
    generated_at: datetime
    tenant_id: UUID
    total_events: int
    by_action: dict[str, int]
    by_transition: dict[str, int]
    created_total: int
    viewed_total: int
    accepted_total: int
    dismissed_total: int
    executed_total: int
    expired_total: int
    superseded_total: int
    reopened_total: int
    timeline: list[RecommendationMetricsTimelinePointResponse]


class RecommendationEngineRunExecutionResponse(BaseModel):
    provider_name: str
    domain: RecommendationDomain
    status: str
    candidate_count: int = 0
    created: int = 0
    updated: int = 0
    errors: int = 0
    duration_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationEngineRunResultResponse(BaseModel):
    run_id: UUID
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    domain: RecommendationDomain | None = None
    dry_run: bool = False
    batch_size: int = 0
    total_batches: int = 0
    providers_requested: int = 0
    providers_executed: int = 0
    candidates_total: int = 0
    recommendations_created: int = 0
    recommendations_updated: int = 0
    errors: int = 0
    duration_ms: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    provider_names: list[str] = Field(default_factory=list)
    executions: list[RecommendationEngineRunExecutionResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
