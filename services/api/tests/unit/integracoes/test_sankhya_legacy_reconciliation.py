# ruff: noqa: S105, S106
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.models import (
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationSyncPolicy,
    IntegrationVersion,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.sankhya.models import SankhyaConfig
from integracoes.sankhya.services.legacy_reconciliation import (
    LegacySankhyaReconciliationState,
    SankhyaLegacyReconciliationService,
)
from integracoes.sankhya.services.sync_service import SankhyaSyncService
from integracoes.security import encrypt_integration_secret


@pytest.fixture(autouse=True)
def _stub_domain_events(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_publish(*args, **kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )


async def _seed_provider(session: AsyncSession, *, active: bool = True) -> MarketplaceIntegracao:
    provider = MarketplaceIntegracao(
        id=2,
        nome="Sankhya",
        slug="sankhya",
        provider_type="ERP",
        ativa=active,
        oficial=True,
        provider_definition={
            "provider_code": "sankhya",
            "provider_name": "Sankhya",
            "display_name": "Sankhya ERP",
        },
        connection_schema={"schema_version": 1},
        credential_schema={"schema_version": 1},
        feature_schema={"capability_matrix": []},
        sync_schema={},
        health_schema={},
    )
    session.add(provider)
    await session.commit()
    return provider


def _legacy_config(tenant_id: str, *, active: bool = True) -> SankhyaConfig:
    return SankhyaConfig(
        id=1,
        tenant_id=tenant_id,
        environment="producao",
        api_base_url="https://gateway.example/api",
        auth_url="https://gateway.example/authenticate",
        client_id="client-123",
        client_secret=encrypt_integration_secret("client-secret"),
        x_token=encrypt_integration_secret("x-token"),
        ws_url=None,
        username=None,
        password=None,
        ativo=active,
        sync_interval=900,
        teste_status=None,
        ultimo_teste=None,
        ultimo_sync=None,
    )


async def _seed_legacy_only(session: AsyncSession, tenant_id: str, *, active: bool = True) -> None:
    session.add(_legacy_config(tenant_id, active=active))
    await session.commit()


async def _materialize_runtime(session: AsyncSession, tenant_id: str) -> None:
    service = SankhyaSyncService(session)
    await service.criar_config(
        tenant_id=tenant_id,
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/authenticate",
        sankhya_client_id="client-123",
        sankhya_client_secret="client-secret",
        sankhya_x_token="x-token",
        sync_interval=900,
    )


async def _count_materialized(session: AsyncSession, tenant_id: str) -> dict[str, int]:
    canonical = await session.scalar(
        select(func.count())
        .select_from(TenantIntegracao)
        .where(TenantIntegracao.tenant_id == tenant_id, TenantIntegracao.deleted_at.is_(None))
    )
    cred = await session.scalar(
        select(func.count())
        .select_from(IntegrationCredential)
        .where(
            IntegrationCredential.tenant_id == tenant_id,
            IntegrationCredential.deleted_at.is_(None),
        )
    )
    features = await session.scalar(
        select(func.count())
        .select_from(IntegrationFeature)
        .where(IntegrationFeature.tenant_id == tenant_id, IntegrationFeature.deleted_at.is_(None))
    )
    policies = await session.scalar(
        select(func.count())
        .select_from(IntegrationSyncPolicy)
        .where(
            IntegrationSyncPolicy.tenant_id == tenant_id,
            IntegrationSyncPolicy.deleted_at.is_(None),
        )
    )
    health = await session.scalar(
        select(func.count()).select_from(IntegrationHealth).where(
            IntegrationHealth.tenant_id == tenant_id
        )
    )
    versions = await session.scalar(
        select(func.count()).select_from(IntegrationVersion).where(
            IntegrationVersion.tenant_id == tenant_id
        )
    )
    return {
        "canonical": int(canonical or 0),
        "credentials": int(cred or 0),
        "features": int(features or 0),
        "policies": int(policies or 0),
        "health": int(health or 0),
        "versions": int(versions or 0),
    }


@pytest.mark.asyncio
async def test_reconcile_legacy_only_dry_run_nao_persiste(
    session: AsyncSession,
) -> None:
    tenant_id = "tenant-legacy-only"
    await _seed_provider(session)
    await _seed_legacy_only(session, tenant_id)

    result = await SankhyaLegacyReconciliationService(session).reconcile_tenant(
        tenant_id,
        dry_run=True,
    )
    counts = await _count_materialized(session, tenant_id)

    assert result.state_before == LegacySankhyaReconciliationState.LEGACY_ONLY.value
    assert result.action == "MATERIALIZE_CANONICAL"
    assert result.blocked is False
    assert result.changed is False
    assert counts == {
        "canonical": 0,
        "credentials": 0,
        "features": 0,
        "policies": 0,
        "health": 0,
        "versions": 0,
    }


@pytest.mark.asyncio
async def test_reconcile_legacy_only_execute_cria_dependencias_e_idempotencia(
    session: AsyncSession,
) -> None:
    tenant_id = "tenant-legacy-execute"
    await _seed_provider(session)
    await _seed_legacy_only(session, tenant_id)

    service = SankhyaLegacyReconciliationService(session)
    result_first = await service.reconcile_tenant(tenant_id, dry_run=False)
    counts_first = await _count_materialized(session, tenant_id)
    result_second = await service.reconcile_tenant(tenant_id, dry_run=False)
    counts_second = await _count_materialized(session, tenant_id)

    assert result_first.state_after == LegacySankhyaReconciliationState.BOTH_CONSISTENT.value
    assert result_first.changed is True
    assert result_first.blocked is False
    assert result_first.scope_type == "TENANT"
    assert result_first.scope_id is None
    assert counts_first == {
        "canonical": 1,
        "credentials": 1,
        "features": 6,
        "policies": 6,
        "health": 1,
        "versions": 1,
    }
    assert result_second.state_before == LegacySankhyaReconciliationState.BOTH_CONSISTENT.value
    assert result_second.action == "NOOP"
    assert result_second.changed is False
    assert counts_second == counts_first


@pytest.mark.asyncio
async def test_reconcile_both_consistent_nao_altera(session: AsyncSession) -> None:
    tenant_id = "tenant-both-consistent"
    await _seed_provider(session)
    await _materialize_runtime(session, tenant_id)

    result = await SankhyaLegacyReconciliationService(session).reconcile_tenant(
        tenant_id,
        dry_run=False,
    )
    counts = await _count_materialized(session, tenant_id)

    assert result.state_before == LegacySankhyaReconciliationState.BOTH_CONSISTENT.value
    assert result.action == "NOOP"
    assert result.changed is False
    assert counts == {
        "canonical": 1,
        "credentials": 1,
        "features": 6,
        "policies": 6,
        "health": 1,
        "versions": 1,
    }


@pytest.mark.asyncio
async def test_reconcile_ignora_credencial_historica_sem_tratar_como_duplicada(
    session: AsyncSession,
) -> None:
    tenant_id = "tenant-historical-credential"
    await _seed_provider(session)
    await _materialize_runtime(session, tenant_id)
    canonical = await session.scalar(
        select(TenantIntegracao).where(TenantIntegracao.tenant_id == tenant_id)
    )
    assert canonical is not None
    session.add(
        IntegrationCredential(
            tenant_id=tenant_id,
            provider_id=canonical.provider_id,
            scope_type=canonical.scope_type,
            segredo_criptografado=encrypt_integration_secret("historical-secret"),
            mask_metadata={"auth_model": "gateway_legacy_login"},
            version_number=99,
            ativo=False,
        )
    )
    await session.commit()

    service = SankhyaLegacyReconciliationService(session)
    service.db.info.pop("tenant_id", None)
    result = await service.reconcile_tenant(tenant_id, dry_run=True)

    assert result.state_before == LegacySankhyaReconciliationState.BOTH_CONSISTENT.value
    assert result.blocked is False
    assert "credenciais canônicas duplicadas" not in result.block_reasons


@pytest.mark.asyncio
async def test_reconcile_both_divergent_bloqueia(session: AsyncSession) -> None:
    tenant_id = "tenant-both-divergent"
    await _seed_provider(session)
    await _materialize_runtime(session, tenant_id)
    await session.execute(
        update(TenantIntegracao)
        .where(TenantIntegracao.tenant_id == tenant_id)
        .values(connection_payload={"sankhya_api_base_url": "https://wrong.example/api"})
    )
    await session.commit()

    result = await SankhyaLegacyReconciliationService(session).reconcile_tenant(
        tenant_id,
        dry_run=True,
    )

    assert result.state_before == LegacySankhyaReconciliationState.BOTH_DIVERGENT.value
    assert result.blocked is True
    assert result.action == "BLOCKED"
    assert result.diff_summary


@pytest.mark.asyncio
async def test_reconcile_canonical_only_nao_altera(session: AsyncSession) -> None:
    tenant_id = "tenant-canonical-only"
    await _seed_provider(session)
    await _materialize_runtime(session, tenant_id)
    await session.execute(delete(SankhyaConfig).where(SankhyaConfig.tenant_id == tenant_id))
    await session.commit()

    result = await SankhyaLegacyReconciliationService(session).reconcile_tenant(
        tenant_id,
        dry_run=True,
    )

    assert result.state_before == LegacySankhyaReconciliationState.CANONICAL_ONLY.value
    assert result.action == "NOOP"
    assert result.blocked is False


@pytest.mark.asyncio
async def test_reconcile_legacy_soft_deleted(session: AsyncSession) -> None:
    tenant_id = "tenant-legacy-soft-deleted"
    await _seed_provider(session)
    await _seed_legacy_only(session, tenant_id, active=False)

    result = await SankhyaLegacyReconciliationService(session).reconcile_tenant(
        tenant_id,
        dry_run=True,
    )

    assert result.state_before == LegacySankhyaReconciliationState.LEGACY_SOFT_DELETED.value
    assert result.blocked is False
    assert result.action == "NOOP"


@pytest.mark.asyncio
async def test_reconcile_canonical_soft_deleted(session: AsyncSession) -> None:
    tenant_id = "tenant-canonical-soft-deleted"
    await _seed_provider(session)
    await _seed_legacy_only(session, tenant_id)
    await _materialize_runtime(session, tenant_id)
    await session.execute(
        update(TenantIntegracao)
        .where(TenantIntegracao.tenant_id == tenant_id)
        .values(deleted_at=datetime.now(timezone.utc))  # noqa: UP017
    )
    await session.commit()

    result = await SankhyaLegacyReconciliationService(session).reconcile_tenant(
        tenant_id,
        dry_run=True,
    )

    assert result.state_before == LegacySankhyaReconciliationState.CANONICAL_SOFT_DELETED.value
    assert result.blocked is False
    assert result.action == "NOOP"


@pytest.mark.asyncio
async def test_reconcile_provider_inativo_bloqueia(session: AsyncSession) -> None:
    tenant_id = "tenant-provider-inactive"
    await _seed_provider(session, active=False)
    await _seed_legacy_only(session, tenant_id)

    result = await SankhyaLegacyReconciliationService(session).reconcile_tenant(
        tenant_id,
        dry_run=True,
    )

    assert result.state_before == LegacySankhyaReconciliationState.LEGACY_ONLY.value
    assert result.blocked is True
    assert "provider sankhya inativo" in " ".join(result.block_reasons)
