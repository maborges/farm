"""Schemas internos do dominio de associacao externa."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from integracoes.models import (
    ExternalRecordAssociationConfidence,
    ExternalRecordAssociationOrigin,
    ExternalRecordAssociationStatus,
    IntegrationScope,
)


class ExternalRecordAssociationCreate(BaseModel):
    tenant_id: str
    provider_id: int
    config_id: int
    feature_id: int | None = None
    environment: str = Field(min_length=1, max_length=50)
    scope_type: IntegrationScope = IntegrationScope.TENANT
    scope_id: str | None = None
    external_company_id: str | None = None
    external_branch_id: str | None = None
    local_entity: str = Field(min_length=1, max_length=100)
    local_record_id: str | None = Field(default=None, min_length=1, max_length=100)
    external_entity: str = Field(min_length=1, max_length=100)
    external_record_id: str = Field(min_length=1, max_length=255)
    secondary_keys: dict[str, str | int | float | bool | None] | None = None
    status: ExternalRecordAssociationStatus = ExternalRecordAssociationStatus.ACTIVE
    origin: ExternalRecordAssociationOrigin = ExternalRecordAssociationOrigin.SYNC_JOB
    confidence: ExternalRecordAssociationConfidence = ExternalRecordAssociationConfidence.MEDIUM
    last_sync_at: datetime | None = None
    last_job_id: UUID | None = None
    notes: str | None = None
    metadata_json: dict[str, str | int | float | bool | None] | None = None
    created_by_usuario_id: str | None = None

    model_config = ConfigDict()


class ExternalRecordAssociationUpdate(BaseModel):
    feature_id: int | None = None
    external_company_id: str | None = None
    external_branch_id: str | None = None
    local_entity: str | None = None
    local_record_id: str | None = Field(default=None, min_length=1, max_length=100)
    secondary_keys: dict[str, str | int | float | bool | None] | None = None
    status: ExternalRecordAssociationStatus | None = None
    confidence: ExternalRecordAssociationConfidence | None = None
    last_sync_at: datetime | None = None
    last_job_id: UUID | None = None
    notes: str | None = None
    metadata_json: dict[str, str | int | float | bool | None] | None = None
    actor_usuario_id: str | None = None
    reason: str | None = None

    model_config = ConfigDict()


class ExternalRecordAssociationReconcile(BaseModel):
    actor_usuario_id: str | None = None
    reason: str | None = None
    local_entity: str | None = None
    local_record_id: str | None = Field(default=None, min_length=1, max_length=100)
    confidence: ExternalRecordAssociationConfidence = (
        ExternalRecordAssociationConfidence.MANUAL_CONFIRMED
    )
    last_job_id: UUID | None = None
    notes: str | None = None

    model_config = ConfigDict()


class ExternalRecordAssociationHistoryItemResponse(BaseModel):
    id: UUID
    tenant_id: str
    link_id: UUID
    event_type: str
    previous_external_record_id: str | None = None
    new_external_record_id: str | None = None
    previous_status: str | None = None
    new_status: str | None = None
    job_id: UUID | None = None
    actor_usuario_id: str | None = None
    reason: str | None = None
    details_payload: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExternalRecordAssociationPendingItemResponse(BaseModel):
    id: UUID
    tenant_id: str
    provider_id: int
    config_id: int
    feature_id: int | None = None
    feature_code: str | None = None
    environment: str
    scope_type: str
    scope_id: str | None = None
    external_company_id: str | None = None
    external_branch_id: str | None = None
    local_entity_type: str
    local_entity_id: str | None = None
    external_entity_type: str
    external_id: str
    external_key: str
    external_payload: dict[str, Any] | None = None
    status: ExternalRecordAssociationStatus
    confidence: ExternalRecordAssociationConfidence
    motivo: str | None = None
    last_sync_at: datetime | None = None
    last_job_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    history: list[ExternalRecordAssociationHistoryItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ExternalRecordAssociationGovernanceReconcileRequest(BaseModel):
    local_entity_type: str = Field(min_length=1, max_length=100)
    local_entity_id: str = Field(min_length=1, max_length=100)
    actor_usuario_id: str | None = None
    reason: str | None = None
    confidence: ExternalRecordAssociationConfidence = (
        ExternalRecordAssociationConfidence.MANUAL_CONFIRMED
    )
    last_job_id: UUID | None = None
    notes: str | None = None

    model_config = ConfigDict()
