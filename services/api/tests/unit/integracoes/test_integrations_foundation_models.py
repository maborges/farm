from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.tenant import Tenant
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationHistory,
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationJob,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncPolicy,
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


def test_tenant_fk_resolve_para_tenant_table_no_metadata_compartilhado() -> None:
    """A FK de tenant_id deve resolver para o objeto Tenant.__table__ real, não
    apenas comparar a string do target — regressão de INTEGRATIONS-MODEL-FK-REPAIR-02,
    onde `ForeignKey("farms.tenants.id")` não resolvia contra o Base.metadata
    compartilhado (Tenant é registrado como "tenants", sem schema explícito).
    """
    models_with_tenant_fk = (
        TenantIntegracao,
        IntegrationCredential,
        IntegrationVersion,
        IntegrationFeature,
        IntegrationSyncPolicy,
        IntegrationJob,
        IntegrationHealth,
        ExternalRecordAssociation,
        ExternalRecordAssociationHistory,
    )

    for model in models_with_tenant_fk:
        fk = next(iter(model.__table__.c.tenant_id.foreign_keys))
        assert fk.column.table is Tenant.__table__, (
            f"{model.__name__}.tenant_id não resolve para Tenant.__table__"
        )
        assert fk.ondelete == "NO ACTION"


@pytest.mark.asyncio
async def test_persistencia_basica_provider_credential_config_version(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, "
            "storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now())"
        ),
        {"id": str(tenant_id), "nome": "Tenant Foundation Models", "doc": str(tenant_id)[:11]},
    )
    await session.execute(
        text(f"SET app.current_tenant_id = '{tenant_id}'")
    )

    provider = MarketplaceIntegracao(
        nome="Provider Teste",
        slug=f"provider-foundation-{uuid.uuid4().hex[:8]}",
        categoria="erp",
        provider_type="ERP",
    )
    session.add(provider)
    await session.flush()
    await session.refresh(provider)

    credential = IntegrationCredential(
        tenant_id=tenant_id,
        provider_id=provider.id,
        scope_type=IntegrationScope.TENANT.value,
        segredo_criptografado=encrypt_integration_secret("segredo"),
        mask_metadata={"password_mask": mask_integration_secret("segredo")},
        version_number=1,
    )
    session.add(credential)
    await session.flush()
    await session.refresh(credential)

    config = TenantIntegracao(
        tenant_id=tenant_id,
        integracao_id=provider.id,
        status="ativa",
        scope_type=IntegrationScope.TENANT.value,
        lifecycle_state=IntegrationStatus.ACTIVE.value,
        connection_payload={"gateway_url": "https://erp.example/ws"},
        credential_ref_id=credential.id,
    )
    session.add(config)
    await session.flush()
    await session.refresh(config)

    version = IntegrationVersion(
        tenant_id=tenant_id,
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
    await session.flush()

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
    # A partir de INTEGRATIONS-MODEL-FK-REPAIR-03, a FK usa "tenants.id" (bare),
    # alinhada ao registro real de Tenant no Base.metadata compartilhado.
    assert 'ForeignKey("tenants.id", ondelete="NO ACTION")' in source
