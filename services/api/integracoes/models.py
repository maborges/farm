"""Modelos canônicos persistentes do domínio de Integrações."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Uuid as UUIDType
from sqlalchemy.orm import relationship, synonym

from core.database import Base


def _tenant_fk() -> ForeignKey:
    return ForeignKey("tenants.id", ondelete="NO ACTION")


class IntegrationScope(str, Enum):
    """Escopos oficiais de configuração de integração."""

    PLATFORM = "PLATFORM"
    TENANT = "TENANT"
    UNIDADE_PRODUTIVA = "UNIDADE_PRODUTIVA"
    ESTABELECIMENTO = "ESTABELECIMENTO"
    USUARIO = "USUARIO"


class IntegrationStatus(str, Enum):
    """Estados oficiais do lifecycle de integração."""

    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONFIGURED = "CONFIGURED"
    VALIDATING = "VALIDATING"
    VALID = "VALID"
    INVALID = "INVALID"
    ACTIVE = "ACTIVE"
    SYNCING = "SYNCING"
    PARTIALLY_DEGRADED = "PARTIALLY_DEGRADED"
    DEGRADED = "DEGRADED"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"
    REMOVED = "REMOVED"


class IntegrationSyncMode(str, Enum):
    """Modos oficiais de sincronização por feature."""

    MANUAL = "MANUAL"
    AGENDADO = "AGENDADO"
    EVENTO = "EVENTO"
    WEBHOOK = "WEBHOOK"
    PULL = "PULL"
    PUSH = "PUSH"


class IntegrationPolicyPriority(str, Enum):
    """Prioridade operacional da política de sync."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class IntegrationJobStatus(str, Enum):
    """Estados operacionais de execução de sync."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"


class IntegrationJobTrigger(str, Enum):
    """Origem de disparo do job."""

    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"
    EVENT = "EVENT"
    WEBHOOK = "WEBHOOK"
    PULL = "PULL"
    PUSH = "PUSH"


class IntegrationHealthStatus(str, Enum):
    """Estados persistidos do health de integração."""

    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    DEGRADED = "DEGRADED"
    AUTH_ERROR = "AUTH_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    RATE_LIMITED = "RATE_LIMITED"


class ExternalRecordAssociationStatus(str, Enum):
    """Estados oficiais da associacao entre registro local e externo."""

    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    CONFLICT = "CONFLICT"
    SUPERSEDED = "SUPERSEDED"
    INACTIVE = "INACTIVE"


class ExternalRecordAssociationOrigin(str, Enum):
    """Origem da criacao ou atualizacao da associacao."""

    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    MANUAL_RECONCILIATION = "MANUAL_RECONCILIATION"
    MIGRATION = "MIGRATION"
    SYNC_JOB = "SYNC_JOB"


class ExternalRecordAssociationConfidence(str, Enum):
    """Nivel de confianca da associacao."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MANUAL_CONFIRMED = "MANUAL_CONFIRMED"


class ExternalRecordAssociationHistoryEvent(str, Enum):
    """Eventos historicos da associacao oficial."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    CONFLICT_MARKED = "CONFLICT_MARKED"
    RECONCILED = "RECONCILED"
    SUPERSEDED = "SUPERSEDED"
    DEACTIVATED = "DEACTIVATED"
    REACTIVATED = "REACTIVATED"


class MarketplaceIntegracao(Base):
    """Catálogo oficial de providers de integração."""

    __tablename__ = "marketplace_integracoes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    descricao = Column(Text)
    descricao_curta = Column(String(200))
    categoria = Column(String(50))
    subcategoria = Column(String(50))
    fornecedor = Column(String(100))
    fornecedor_logo = Column(String(500))
    site_fornecedor = Column(String(500))
    suporte_email = Column(String(200))
    ativa = Column(Boolean, default=True)
    oficial = Column(Boolean, default=False)
    versao = Column(String(20))
    requisitos = Column(JSON)
    configuracoes = Column(JSON)
    total_instalacoes = Column(Integer, default=0)
    avaliacao_media = Column(Float, default=0)
    total_avaliacoes = Column(Integer, default=0)
    logo_url = Column(String(500))
    screenshots = Column(JSON)
    documentacao_url = Column(String(500))
    provider_type = Column(String(50), nullable=False, default="GENERIC")
    provider_definition = Column(JSON)
    connection_schema = Column(JSON)
    credential_schema = Column(JSON)
    feature_schema = Column(JSON)
    sync_schema = Column(JSON)
    health_schema = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TenantIntegracao(Base):
    """Configuração canônica de integração por tenant/escopo."""

    __tablename__ = "tenant_integracoes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    integracao_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
    status = Column(String(50), default="ativa")
    configuracoes = Column(JSON, default={})
    credenciais = Column(JSON)
    webhook_url = Column(String(500))
    webhook_secret = Column(String(200))
    ultima_sincronizacao = Column(DateTime)
    total_sincronizacoes = Column(Integer, default=0)
    installed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scope_type = Column(String(30), nullable=False, default=IntegrationScope.TENANT.value)
    scope_id = Column(String(50))
    lifecycle_state = Column(
        String(30),
        nullable=False,
        default=IntegrationStatus.CONFIGURED.value,
    )
    connection_payload = Column(JSON)
    credential_ref_id = Column(Integer, ForeignKey("integration_credentials.id"))
    deleted_at = Column(DateTime)

    # lazy default (não "noload"): estas duas relações são carregadas via
    # selectinload() explícito em sync_service.py e legacy_reconciliation.py —
    # "noload" no mapper bloquearia esses eager-loads explícitos.
    integracao = relationship("MarketplaceIntegracao")
    credential = relationship("IntegrationCredential", foreign_keys=[credential_ref_id])

    provider_id = synonym("integracao_id")


class BalancaInboundEvent(Base):
    """Evento recebido do Pondaxis, persistido para deduplicação e auditoria."""

    __tablename__ = "balanca_inbound_events"

    event_id = Column(UUIDType(as_uuid=True), primary_key=True)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    account_id = Column(UUIDType(as_uuid=True), nullable=False)
    event_type = Column(String(120), nullable=False)
    idempotency_key = Column(String(180), nullable=False)
    payload = Column(JSON, nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("tenant_id", "event_id", name="uq_balanca_inbound_events_tenant_event"),
        Index("ix_balanca_inbound_events_tenant_received", "tenant_id", "received_at"),
    )


class BalancaWebhookCredential(Base):
    """Credencial HMAC persistida para uma Conta Pondaxis consumidora."""

    __tablename__ = "balanca_webhook_credentials"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    balanca_account_id = Column(UUIDType(as_uuid=True), nullable=False, unique=True, index=True)
    segredo_criptografado = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="ATIVO")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    rotated_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IntegrationCredential(Base):
    """Credencial canônica de integração com segredo criptografado."""

    __tablename__ = "integration_credentials"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider_id",
            "scope_type",
            "scope_id",
            "version_number",
            name="uq_integration_credentials_version_scope",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
    scope_type = Column(String(30), nullable=False, default=IntegrationScope.TENANT.value)
    scope_id = Column(String(50))
    segredo_criptografado = Column(Text, nullable=False)
    mask_metadata = Column(JSON)
    version_number = Column(Integer, nullable=False, default=1)
    ativo = Column(Boolean, nullable=False, default=True)
    created_by_usuario_id = Column(String(50))
    rotated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime)

    provider = relationship("MarketplaceIntegracao", lazy="noload")


class IntegrationVersion(Base):
    """Snapshot versionado e mascarado da configuração canônica."""

    __tablename__ = "integration_versions"
    __table_args__ = (
        UniqueConstraint(
            "config_id",
            "version_number",
            name="uq_integration_versions_config_version",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    config_id = Column(Integer, ForeignKey("tenant_integracoes.id"), nullable=False)
    credential_ref_id = Column(Integer, ForeignKey("integration_credentials.id"))
    version_number = Column(Integer, nullable=False, default=1)
    snapshot_mascarado = Column(JSON, nullable=False)
    motivo = Column(String(200))
    autor_usuario_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    config = relationship("TenantIntegracao", foreign_keys=[config_id], lazy="noload")
    credential = relationship("IntegrationCredential", foreign_keys=[credential_ref_id], lazy="noload")


class IntegrationFeature(Base):
    """Capacidade canônica habilitada por configuração de integração."""

    __tablename__ = "integration_features"
    __table_args__ = (
        UniqueConstraint(
            "config_id",
            "codigo",
            name="uq_integration_features_config_codigo",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    config_id = Column(Integer, ForeignKey("tenant_integracoes.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
    codigo = Column(String(80), nullable=False)
    nome = Column(String(120), nullable=False)
    descricao = Column(Text)
    habilitada = Column(Boolean, nullable=False, default=True)
    obrigatoria = Column(Boolean, nullable=False, default=False)
    settings_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime)

    config = relationship("TenantIntegracao", foreign_keys=[config_id], lazy="noload")
    provider = relationship("MarketplaceIntegracao", foreign_keys=[provider_id], lazy="noload")


class IntegrationSyncPolicy(Base):
    """Política operacional canônica de sincronização por feature."""

    __tablename__ = "integration_sync_policies"
    __table_args__ = (
        UniqueConstraint(
            "feature_id",
            name="uq_integration_sync_policies_feature_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    config_id = Column(Integer, ForeignKey("tenant_integracoes.id"), nullable=False)
    feature_id = Column(Integer, ForeignKey("integration_features.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
    mode = Column(String(30), nullable=False, default=IntegrationSyncMode.MANUAL.value)
    prioridade = Column(String(20), nullable=False, default=IntegrationPolicyPriority.NORMAL.value)
    retry_ativo = Column(Boolean, nullable=False, default=True)
    retry_limite = Column(Integer, nullable=False, default=3)
    batch_size = Column(Integer, nullable=False, default=100)
    backoff_seconds = Column(Integer, nullable=False, default=30)
    timeout_seconds = Column(Integer, nullable=False, default=300)
    idempotencia_ativa = Column(Boolean, nullable=False, default=True)
    trigger_expression = Column(String(120))
    settings_payload = Column(JSON)
    ativa = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime)

    config = relationship("TenantIntegracao", foreign_keys=[config_id], lazy="noload")
    feature = relationship("IntegrationFeature", foreign_keys=[feature_id], lazy="noload")
    provider = relationship("MarketplaceIntegracao", foreign_keys=[provider_id], lazy="noload")


class IntegrationJob(Base):
    """Execução operacional de sincronização sem substituir o Outbox."""

    __tablename__ = "integration_jobs"

    id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    config_id = Column(Integer, ForeignKey("tenant_integracoes.id"), nullable=False)
    feature_id = Column(Integer, ForeignKey("integration_features.id"))
    sync_policy_id = Column(Integer, ForeignKey("integration_sync_policies.id"))
    provider_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
    status = Column(String(20), nullable=False, default=IntegrationJobStatus.PENDING.value)
    trigger_type = Column(String(20), nullable=False, default=IntegrationJobTrigger.MANUAL.value)
    outbox_event_id = Column(UUIDType(as_uuid=True), ForeignKey("domain_event_outbox.id"))
    correlation_id = Column(UUIDType(as_uuid=True))
    causation_id = Column(UUIDType(as_uuid=True))
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    retry_count = Column(Integer, nullable=False, default=0)
    processados = Column(Integer, nullable=False, default=0)
    sucessos = Column(Integer, nullable=False, default=0)
    erros = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    request_payload = Column(JSON)
    result_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    config = relationship("TenantIntegracao", foreign_keys=[config_id], lazy="noload")
    feature = relationship("IntegrationFeature", foreign_keys=[feature_id], lazy="noload")
    sync_policy = relationship("IntegrationSyncPolicy", foreign_keys=[sync_policy_id], lazy="noload")
    provider = relationship("MarketplaceIntegracao", foreign_keys=[provider_id], lazy="noload")


class IntegrationHealth(Base):
    """Snapshot operacional persistente do health da integração."""

    __tablename__ = "integration_health_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "config_id",
            name="uq_integration_health_config_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    config_id = Column(Integer, ForeignKey("tenant_integracoes.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
    last_job_id = Column(UUIDType(as_uuid=True), ForeignKey("integration_jobs.id"))
    status = Column(
        String(30),
        nullable=False,
        default=IntegrationHealthStatus.DISCONNECTED.value,
    )
    summary = Column(String(200))
    details_payload = Column(JSON)
    latency_ms = Column(Integer)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_success_at = Column(DateTime(timezone=True))
    last_failure_at = Column(DateTime(timezone=True))
    rate_limited_until = Column(DateTime(timezone=True))
    checked_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    config = relationship("TenantIntegracao", foreign_keys=[config_id], lazy="noload")
    provider = relationship("MarketplaceIntegracao", foreign_keys=[provider_id], lazy="noload")
    last_job = relationship("IntegrationJob", foreign_keys=[last_job_id], lazy="noload")


class ExternalRecordAssociation(Base):
    """Associacao oficial entre um registro local e um registro externo."""

    __tablename__ = "integration_external_record_links"
    __table_args__ = (
        Index(
            "ix_external_record_links_tenant_local",
            "tenant_id",
            "local_entity",
            "local_record_id",
        ),
        Index(
            "ix_external_record_links_tenant_external",
            "tenant_id",
            "provider_id",
            "external_entity",
            "external_record_id",
        ),
        Index(
            "ix_external_record_links_tenant_status",
            "tenant_id",
            "status",
        ),
    )

    id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
    config_id = Column(Integer, ForeignKey("tenant_integracoes.id"), nullable=False)
    feature_id = Column(Integer, ForeignKey("integration_features.id"))
    environment = Column(String(50), nullable=False)
    scope_type = Column(String(30), nullable=False, default=IntegrationScope.TENANT.value)
    scope_id = Column(String(50))
    external_company_id = Column(String(50))
    external_branch_id = Column(String(50))
    local_entity = Column(String(100), nullable=False)
    local_record_id = Column(String(100))
    external_entity = Column(String(100), nullable=False)
    external_record_id = Column(String(255), nullable=False)
    secondary_keys = Column(JSON)
    status = Column(
        String(30),
        nullable=False,
        default=ExternalRecordAssociationStatus.ACTIVE.value,
    )
    origin = Column(
        String(40),
        nullable=False,
        default=ExternalRecordAssociationOrigin.SYNC_JOB.value,
    )
    confidence = Column(
        String(30),
        nullable=False,
        default=ExternalRecordAssociationConfidence.MEDIUM.value,
    )
    last_sync_at = Column(DateTime(timezone=True))
    last_job_id = Column(UUIDType(as_uuid=True), ForeignKey("integration_jobs.id"))
    notes = Column(Text)
    metadata_json = Column(JSON)
    created_by_usuario_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime)

    provider = relationship("MarketplaceIntegracao", foreign_keys=[provider_id], lazy="noload")
    config = relationship("TenantIntegracao", foreign_keys=[config_id], lazy="noload")
    feature = relationship("IntegrationFeature", foreign_keys=[feature_id], lazy="noload")
    last_job = relationship("IntegrationJob", foreign_keys=[last_job_id], lazy="noload")


class ExternalRecordAssociationHistory(Base):
    """Historico de alteracoes da associacao oficial."""

    __tablename__ = "integration_external_record_link_history"
    __table_args__ = (
        Index(
            "ix_external_record_link_history_tenant_link",
            "tenant_id",
            "link_id",
        ),
        Index(
            "ix_external_record_link_history_tenant_event",
            "tenant_id",
            "event_type",
        ),
    )

    id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
    link_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("integration_external_record_links.id"),
        nullable=False,
    )
    event_type = Column(String(30), nullable=False)
    previous_external_record_id = Column(String(255))
    new_external_record_id = Column(String(255))
    previous_status = Column(String(30))
    new_status = Column(String(30))
    job_id = Column(UUIDType(as_uuid=True), ForeignKey("integration_jobs.id"))
    actor_usuario_id = Column(String(50))
    reason = Column(String(255))
    details_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    link = relationship("ExternalRecordAssociation", foreign_keys=[link_id], lazy="noload")
    job = relationship("IntegrationJob", foreign_keys=[job_id], lazy="noload")
