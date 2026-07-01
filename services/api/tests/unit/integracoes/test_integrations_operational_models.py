from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from alert_engine.models import Domain
from integracoes.events import (
    IntegrationActivated,
    IntegrationConfigured,
    IntegrationCredentialRotated,
    IntegrationDisabled,
    IntegrationHealthChanged,
    IntegrationSyncCompleted,
    IntegrationSyncFailed,
    IntegrationSyncStarted,
)
from integracoes.models import (
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationJob,
    IntegrationJobStatus,
    IntegrationJobTrigger,
    IntegrationPolicyPriority,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncMode,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.security import encrypt_integration_secret

REPO_ROOT = Path(__file__).resolve().parents[5]
MODELS_FILE = REPO_ROOT / "services/api/integracoes/models.py"
EVENTS_FILE = REPO_ROOT / "services/api/integracoes/events.py"
MIGRATION_FILE = (
    REPO_ROOT
    / "services/api/migrations/versions/20260701_integrations_domain_03b_operations.py"
)
SANKHYA_MODELS = REPO_ROOT / "services/api/integracoes/sankhya/models/__init__.py"
ALERT_MODELS = REPO_ROOT / "services/api/alert_engine/models.py"


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    MarketplaceIntegracao.__table__.create(engine)
    IntegrationCredential.__table__.create(engine)
    TenantIntegracao.__table__.create(engine)
    IntegrationFeature.__table__.create(engine)
    IntegrationSyncPolicy.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    return factory()


def test_sync_mode_enum_permanece_estavel() -> None:
    assert [mode.value for mode in IntegrationSyncMode] == [
        "MANUAL",
        "AGENDADO",
        "EVENTO",
        "WEBHOOK",
        "PULL",
        "PUSH",
    ]


def test_priority_job_trigger_e_health_enums_permancem_estaveis() -> None:
    assert [priority.value for priority in IntegrationPolicyPriority] == [
        "LOW",
        "NORMAL",
        "HIGH",
        "URGENT",
    ]
    assert [status.value for status in IntegrationJobStatus] == [
        "PENDING",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        "CANCELLED",
        "RETRYING",
    ]
    assert [trigger.value for trigger in IntegrationJobTrigger] == [
        "MANUAL",
        "SCHEDULED",
        "EVENT",
        "WEBHOOK",
        "PULL",
        "PUSH",
    ]
    assert [status.value for status in IntegrationHealthStatus] == [
        "CONNECTED",
        "DISCONNECTED",
        "DEGRADED",
        "AUTH_ERROR",
        "CONFIG_ERROR",
        "PARTIAL_FAILURE",
        "RATE_LIMITED",
    ]


def test_modelos_operacionais_expoem_colunas_canonicas() -> None:
    feature_columns = set(IntegrationFeature.__table__.c.keys())
    policy_columns = set(IntegrationSyncPolicy.__table__.c.keys())
    job_columns = set(IntegrationJob.__table__.c.keys())
    health_columns = set(IntegrationHealth.__table__.c.keys())

    assert {"tenant_id", "config_id", "provider_id", "codigo", "habilitada"} <= feature_columns
    assert {
        "mode",
        "prioridade",
        "retry_limite",
        "batch_size",
        "idempotencia_ativa",
    } <= policy_columns
    assert {
        "outbox_event_id",
        "status",
        "trigger_type",
        "processados",
        "sucessos",
        "erros",
    } <= job_columns
    assert {"last_job_id", "status", "consecutive_failures", "checked_at"} <= health_columns


def test_persistencia_basica_feature_e_policy() -> None:
    session = _build_session()

    provider = MarketplaceIntegracao(
        nome="Sankhya",
        slug="sankhya-operacoes",
        categoria="erp",
        provider_type="ERP",
    )
    session.add(provider)
    session.commit()
    session.refresh(provider)

    credential = IntegrationCredential(
        tenant_id="tenant-ops",
        provider_id=provider.id,
        scope_type=IntegrationScope.TENANT.value,
        segredo_criptografado=encrypt_integration_secret("segredo-operacional"),
        version_number=1,
    )
    session.add(credential)
    session.commit()
    session.refresh(credential)

    config = TenantIntegracao(
        tenant_id="tenant-ops",
        integracao_id=provider.id,
        scope_type=IntegrationScope.TENANT.value,
        lifecycle_state=IntegrationStatus.ACTIVE.value,
        credential_ref_id=credential.id,
    )
    session.add(config)
    session.commit()
    session.refresh(config)

    feature = IntegrationFeature(
        tenant_id="tenant-ops",
        config_id=config.id,
        provider_id=provider.id,
        codigo="produtos",
        nome="Produtos",
        habilitada=True,
    )
    session.add(feature)
    session.commit()
    session.refresh(feature)

    policy = IntegrationSyncPolicy(
        tenant_id="tenant-ops",
        config_id=config.id,
        feature_id=feature.id,
        provider_id=provider.id,
        mode=IntegrationSyncMode.EVENTO.value,
        prioridade=IntegrationPolicyPriority.HIGH.value,
    )
    session.add(policy)
    session.commit()
    session.refresh(policy)

    assert policy.feature_id == feature.id
    assert policy.config_id == config.id
    assert policy.mode == IntegrationSyncMode.EVENTO.value


def test_job_modelo_se_relaciona_ao_outbox_sem_substituir_fila() -> None:
    source = MODELS_FILE.read_text(encoding="utf-8")
    migration = MIGRATION_FILE.read_text(encoding="utf-8")

    assert (
        'outbox_event_id = Column(UUIDType(as_uuid=True), ForeignKey("domain_event_outbox.id"))'
        in source
    )
    assert 'OUTBOX_TABLE = "domain_event_outbox"' in migration
    assert 'ForeignKeyConstraint(["outbox_event_id"], [f"{OUTBOX_TABLE}.id"])' in migration


def test_dominio_integrations_foi_adicionado_ao_alert_engine_sem_motor_paralelo() -> None:
    alert_source = ALERT_MODELS.read_text(encoding="utf-8")
    event_source = EVENTS_FILE.read_text(encoding="utf-8")

    assert 'INTEGRATIONS = "INTEGRATIONS"' in alert_source
    assert "domain: Domain = Domain.INTEGRATIONS" in event_source
    assert "integration_alerts" not in MODELS_FILE.read_text(encoding="utf-8")


def test_eventos_canonicos_permanecem_tipados_no_dominio_integrations() -> None:
    tenant_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    job_id = uuid.uuid4()

    configured = IntegrationConfigured(
        tenant_id=tenant_id,
        entity_id=entity_id,
        provider_id=1,
        config_id=10,
    )
    activated = IntegrationActivated(
        tenant_id=tenant_id,
        entity_id=entity_id,
        provider_id=1,
        config_id=10,
    )
    disabled = IntegrationDisabled(
        tenant_id=tenant_id,
        entity_id=entity_id,
        provider_id=1,
        config_id=10,
    )
    rotated = IntegrationCredentialRotated(
        tenant_id=tenant_id,
        entity_id=entity_id,
        provider_id=1,
        config_id=10,
        credential_id=100,
    )
    started = IntegrationSyncStarted(
        tenant_id=tenant_id,
        entity_id=entity_id,
        provider_id=1,
        config_id=10,
        job_id=job_id,
    )
    completed = IntegrationSyncCompleted(
        tenant_id=tenant_id,
        entity_id=entity_id,
        provider_id=1,
        config_id=10,
        job_id=job_id,
        processed=30,
        succeeded=29,
        failed=1,
    )
    failed = IntegrationSyncFailed(
        tenant_id=tenant_id,
        entity_id=entity_id,
        provider_id=1,
        config_id=10,
        job_id=job_id,
        error_message="falha externa",
    )
    health = IntegrationHealthChanged(
        tenant_id=tenant_id,
        entity_id=entity_id,
        provider_id=1,
        config_id=10,
        current_status=IntegrationHealthStatus.DEGRADED.value,
    )

    assert configured.domain == Domain.INTEGRATIONS
    assert activated.event_type == "integrations.activated"
    assert disabled.event_type == "integrations.disabled"
    assert rotated.credential_id == 100
    assert started.entity_type == "integration_job"
    assert completed.succeeded == 29
    assert failed.error_message == "falha externa"
    assert health.current_status == IntegrationHealthStatus.DEGRADED.value


def test_notifications_e_auditoria_reutilizam_infraestrutura_existente() -> None:
    event_source = EVENTS_FILE.read_text(encoding="utf-8")
    models_source = MODELS_FILE.read_text(encoding="utf-8")

    assert "notificacoes" not in event_source
    assert "TenantAuditLog" not in models_source
    assert "AdminAuditLog" not in models_source
    assert "integration_notifications" not in models_source
    assert "integration_audit_log" not in models_source


def test_migration_materializa_rls_e_constraints_nas_tabelas_operacionais() -> None:
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert "_enable_string_tenant_rls(FEATURE_TABLE)" in source
    assert "_enable_string_tenant_rls(SYNC_POLICY_TABLE)" in source
    assert "_enable_string_tenant_rls(JOB_TABLE)" in source
    assert "_enable_string_tenant_rls(HEALTH_TABLE)" in source
    assert "ck_integration_sync_policies_mode" in source
    assert "ck_integration_jobs_status" in source
    assert "ck_integration_health_snapshots_status" in source


def test_metadata_do_alembic_importa_modelos_canonicos_de_integracoes() -> None:
    source = (REPO_ROOT / "services/api/migrations/env.py").read_text(encoding="utf-8")

    assert "from integracoes.models import (" in source
    assert "IntegrationFeature" in source
    assert "IntegrationSyncPolicy" in source
    assert "IntegrationJob" in source
    assert "IntegrationHealth" in source


def test_sankhya_permanece_provider_specific_sem_acoplamento_direto_a_novos_models() -> None:
    source = SANKHYA_MODELS.read_text(encoding="utf-8")

    assert "class SankhyaConfig" in source
    assert "class SankhyaSyncLog" in source
    assert "IntegrationFeature" not in source
    assert "IntegrationJob" not in source


def test_relacionamentos_basicos_estao_definidos() -> None:
    job_relationships = set(inspect(IntegrationJob).relationships.keys())
    health_relationships = set(inspect(IntegrationHealth).relationships.keys())

    assert job_relationships >= {"config", "feature", "sync_policy", "provider"}
    assert health_relationships >= {"config", "provider", "last_job"}
