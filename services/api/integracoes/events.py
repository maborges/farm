"""Contratos canônicos de eventos do domínio de Integrações."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from alert_engine.models import Domain
from events.base import DomainEvent


class IntegrationDomainEvent(DomainEvent):
    """Envelope base para eventos canônicos de Integrações."""

    domain: Domain = Domain.INTEGRATIONS
    source_type: str = "integration"
    entity_type: str = "integration_config"


class IntegrationConfigured(IntegrationDomainEvent):
    event_type: Literal["integrations.configured"] = "integrations.configured"
    source_type: str = "integration.config"
    provider_id: int
    config_id: int


class IntegrationActivated(IntegrationDomainEvent):
    event_type: Literal["integrations.activated"] = "integrations.activated"
    source_type: str = "integration.config"
    provider_id: int
    config_id: int


class IntegrationDisabled(IntegrationDomainEvent):
    event_type: Literal["integrations.disabled"] = "integrations.disabled"
    source_type: str = "integration.config"
    provider_id: int
    config_id: int


class IntegrationCredentialRotated(IntegrationDomainEvent):
    event_type: Literal["integrations.credential_rotated"] = (
        "integrations.credential_rotated"
    )
    source_type: str = "integration.credential"
    provider_id: int
    config_id: int
    credential_id: int


class IntegrationSyncStarted(IntegrationDomainEvent):
    event_type: Literal["integrations.sync_started"] = "integrations.sync_started"
    source_type: str = "integration.job"
    entity_type: str = "integration_job"
    provider_id: int
    config_id: int
    job_id: UUID
    feature_code: str | None = None


class IntegrationSyncCompleted(IntegrationDomainEvent):
    event_type: Literal["integrations.sync_completed"] = "integrations.sync_completed"
    source_type: str = "integration.job"
    entity_type: str = "integration_job"
    provider_id: int
    config_id: int
    job_id: UUID
    feature_code: str | None = None
    processed: int = 0
    succeeded: int = 0
    failed: int = 0


class IntegrationSyncFailed(IntegrationDomainEvent):
    event_type: Literal["integrations.sync_failed"] = "integrations.sync_failed"
    source_type: str = "integration.job"
    entity_type: str = "integration_job"
    provider_id: int
    config_id: int
    job_id: UUID
    feature_code: str | None = None
    error_message: str | None = None


class IntegrationHealthChanged(IntegrationDomainEvent):
    event_type: Literal["integrations.health_changed"] = "integrations.health_changed"
    source_type: str = "integration.health"
    entity_type: str = "integration_health"
    provider_id: int
    config_id: int
    previous_status: str | None = None
    current_status: str
