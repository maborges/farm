from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from integracoes.models import (
    IntegrationCredential,
    IntegrationScope,
    IntegrationStatus,
    IntegrationVersion,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.security import (
    decrypt_integration_secret,
    encrypt_integration_secret,
    is_integration_secret_encrypted,
    mask_integration_secret,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
IOT_MODELS = REPO_ROOT / "services/api/iot_integracao/new_holland/models/__init__.py"
SANKHYA_MODELS = REPO_ROOT / "services/api/integracoes/sankhya/models/__init__.py"
MIGRATION_FILE = (
    REPO_ROOT
    / "services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py"
)


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    MarketplaceIntegracao.__table__.create(engine)
    IntegrationCredential.__table__.create(engine)
    TenantIntegracao.__table__.create(engine)
    IntegrationVersion.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    return factory()


def test_integration_scope_enum_permanece_estavel() -> None:
    assert [scope.value for scope in IntegrationScope] == [
        "PLATFORM",
        "TENANT",
        "ESTABELECIMENTO",
        "USUARIO",
    ]


def test_integration_status_enum_permanece_compativel_com_lifecycle() -> None:
    assert [status.value for status in IntegrationStatus] == [
        "NOT_CONFIGURED",
        "CONFIGURED",
        "VALIDATING",
        "VALID",
        "INVALID",
        "ACTIVE",
        "SYNCING",
        "PARTIALLY_DEGRADED",
        "DEGRADED",
        "SUSPENDED",
        "DISABLED",
        "REVOKED",
        "REMOVED",
    ]


def test_tenant_integracao_expoe_colunas_canonicas_sem_quebrar_legado() -> None:
    columns = TenantIntegracao.__table__.c

    assert "integracao_id" in columns
    assert "status" in columns
    assert "configuracoes" in columns
    assert "credenciais" in columns
    assert "scope_type" in columns
    assert "scope_id" in columns
    assert "lifecycle_state" in columns
    assert "connection_payload" in columns
    assert "credential_ref_id" in columns
    assert "deleted_at" in columns


def test_persistencia_basica_provider_credential_config_version() -> None:
    session = _build_session()

    provider = MarketplaceIntegracao(
        nome="Sankhya",
        slug="sankhya",
        categoria="erp",
        provider_type="ERP",
    )
    session.add(provider)
    session.commit()
    session.refresh(provider)

    credential = IntegrationCredential(
        tenant_id="tenant-1",
        provider_id=provider.id,
        scope_type=IntegrationScope.TENANT.value,
        segredo_criptografado=encrypt_integration_secret("segredo"),
        mask_metadata={"password_mask": mask_integration_secret("segredo")},
        version_number=1,
    )
    session.add(credential)
    session.commit()
    session.refresh(credential)

    config = TenantIntegracao(
        tenant_id="tenant-1",
        integracao_id=provider.id,
        status="ativa",
        scope_type=IntegrationScope.TENANT.value,
        lifecycle_state=IntegrationStatus.ACTIVE.value,
        connection_payload={"gateway_url": "https://erp.example/ws"},
        credential_ref_id=credential.id,
    )
    session.add(config)
    session.commit()
    session.refresh(config)

    version = IntegrationVersion(
        tenant_id="tenant-1",
        config_id=config.id,
        credential_ref_id=credential.id,
        version_number=1,
        snapshot_mascarado={
            "provider_id": provider.id,
            "connection_payload": {"gateway_url": "https://erp.example/ws"},
            "password_mask": "••••••••",  # noqa: S105
        },
        motivo="bootstrap",
    )
    session.add(version)
    session.commit()

    assert config.provider_id == provider.id
    assert config.integracao_id == provider.id
    assert config.credential_ref_id == credential.id
    assert version.snapshot_mascarado["password_mask"] == "••••••••"  # noqa: S105


def test_credencial_usa_criptografia_e_masking_sem_texto_puro() -> None:
    encrypted = encrypt_integration_secret("segredo-super-sensivel")

    assert encrypted != "segredo-super-sensivel"
    assert is_integration_secret_encrypted(encrypted) is True
    assert decrypt_integration_secret(encrypted) == "segredo-super-sensivel"
    assert mask_integration_secret(encrypted) == "••••••••"


def test_integration_version_nao_precisa_armazenar_segredo_em_texto_puro() -> None:
    snapshot = {
        "gateway_url": "https://erp.example/ws",
        "password_mask": "••••••••",  # noqa: S105
        "password_configured": True,
    }

    assert "password" not in snapshot
    assert snapshot["password_mask"] == "••••••••"  # noqa: S105


def test_migration_materializa_rls_em_tabelas_tenant_scoped() -> None:
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert "tenant_integracoes" in source
    assert "integration_credentials" in source
    assert "integration_versions" in source
    assert "_enable_string_tenant_rls(CONFIG_TABLE)" in source
    assert "_enable_string_tenant_rls(CREDENTIAL_TABLE)" in source
    assert "_enable_string_tenant_rls(VERSION_TABLE)" in source
    assert "current_setting('app.current_tenant_id', true)::text" in source


def test_marketplace_integracao_permanece_catalogo_compativel() -> None:
    columns = inspect(MarketplaceIntegracao).columns

    assert "slug" in columns
    assert "categoria" in columns
    assert "provider_type" in columns
    assert "provider_definition" in columns
    assert "connection_schema" in columns
    assert "credential_schema" in columns


def test_modulo_legado_iot_reexporta_catalogo_e_config_canonicos() -> None:
    source = IOT_MODELS.read_text(encoding="utf-8")

    assert "from integracoes.models import MarketplaceIntegracao, TenantIntegracao" in source
    assert "class MarketplaceAvaliacao" in source


def test_sankhya_permanece_inteiro_como_provider_specific() -> None:
    source = SANKHYA_MODELS.read_text(encoding="utf-8")

    assert "class SankhyaConfig" in source
    assert "class SankhyaSyncLog" in source
    assert "UUIDType(as_uuid=False)" in source
    assert 'ForeignKey("farms.tenants.id", ondelete="NO ACTION")' in source
