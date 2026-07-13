"""Schemas internos do dominio de associacao externa."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class PaginatedExternalRecordAssociationResponse(BaseModel):
    items: list[ExternalRecordAssociationPendingItemResponse]
    total: int
    total_filtered: int
    limit: int
    offset: int

    model_config = ConfigDict()


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


class ExternalRecordAssociationSummaryResponse(BaseModel):
    PENDING: int = 0
    CONFLICT: int = 0
    ACTIVE: int = 0
    SUPERSEDED: int = 0
    INACTIVE: int = 0
    TOTAL: int = 0

    model_config = ConfigDict()


class ProviderFieldType(str, Enum):
    STRING = "string"
    SECRET = "secret"
    URL = "url"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    SELECT = "select"


class ProviderFieldValidation(BaseModel):
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None


class ProviderFieldSelectOption(BaseModel):
    value: str | int | bool
    label: str


class ProviderFieldDefinition(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type: ProviderFieldType
    required: bool = False
    secret: bool = False
    placeholder: str | None = None
    help_text: str | None = None
    default: Any | None = None
    order: int = 0
    options: list[ProviderFieldSelectOption] | None = None
    validation: ProviderFieldValidation | None = None

    @model_validator(mode="after")
    def validate_rules(self) -> ProviderFieldDefinition:
        if self.type == ProviderFieldType.SELECT and not self.options:
            raise ValueError("Fields of type 'select' must provide options.")
        if self.type != ProviderFieldType.SELECT and self.options is not None:
            raise ValueError("Only 'select' fields can have options.")
        if self.secret and self.default is not None:
            raise ValueError("Secret fields cannot have default values.")
        return self


class ProviderSchemaDefinition(BaseModel):
    schema_version: int = 1
    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    fields: list[ProviderFieldDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_keys(self) -> ProviderSchemaDefinition:
        keys = [f.key for f in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate keys found in fields.")
        return self


class ProviderPublicIdentity(BaseModel):
    id: int
    slug: str
    nome: str
    descricao_curta: str | None = None
    logo_url: str | None = None
    provider_type: str
    ativa: bool
    oficial: bool
    versao: str | None = None


class ProviderSchemaResponse(BaseModel):
    provider: ProviderPublicIdentity
    schema_version: int = 1
    connection_schema: ProviderSchemaDefinition | dict[str, Any] | None = None
    credential_schema: ProviderSchemaDefinition | dict[str, Any] | None = None
