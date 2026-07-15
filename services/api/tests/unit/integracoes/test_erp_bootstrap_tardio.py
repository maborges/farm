# ruff: noqa: S105, S106
from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import core.dependencies as core_dependencies
import integracoes.erp.router as erp_router_module
import integracoes.sankhya.routers as sankhya_router_module
from integracoes.models import (
    IntegrationCredential,
    IntegrationFeature,
    IntegrationStatus,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.sankhya.models import SankhyaConfig
from integracoes.sankhya.services.sync_service import SankhyaSyncService


async def _seed_sankhya_provider(session: AsyncSession) -> None:
    existing = await session.execute(
        select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == "sankhya")
    )
    if existing.scalar_one_or_none() is not None:
        return
    session.add(
        MarketplaceIntegracao(
            id=2,
            nome="Sankhya",
            slug="sankhya",
            provider_type="ERP",
            ativa=True,
            oficial=True,
            provider_definition={
                "provider_code": "sankhya",
                "provider_name": "Sankhya",
                "display_name": "Sankhya ERP",
                "supported_scopes": ["TENANT"],
                "authentication_models": ["gateway_oauth_client_credentials"],
                "supported_versions": ["v1"],
            },
            connection_schema={
                "schema_version": 1,
                "required": [
                    "sankhya_environment",
                    "sankhya_api_base_url",
                    "sankhya_auth_url",
                    "sync_interval",
                ],
                "optional": ["auth_model"],
                "fields": [],
            },
            credential_schema={
                "schema_version": 1,
                "required": [
                    "sankhya_client_id",
                    "sankhya_client_secret",
                    "sankhya_x_token",
                ],
                "optional": [],
                "fields": [],
            },
            feature_schema={"capability_matrix": []},
            sync_schema={},
            health_schema={},
        )
    )
    await session.commit()


def _override_permission_dependencies(app: FastAPI) -> None:
    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        for dependency in dependant.dependencies:
            call = getattr(dependency, "call", None)
            if call is None:
                continue
            if call.__module__ == "core.dependencies" and call.__name__ == "_dependency":
                app.dependency_overrides[call] = lambda: True


def _build_client(session: AsyncSession, tenant_id: uuid.UUID) -> AsyncClient:
    app = FastAPI()
    app.include_router(erp_router_module.router, prefix="/api/v1/integracoes")
    app.include_router(sankhya_router_module.router, prefix="/api/v1/integracoes")
    app.dependency_overrides[core_dependencies.get_session] = lambda: session
    app.dependency_overrides[erp_router_module.get_session] = lambda: session
    app.dependency_overrides[sankhya_router_module.get_session] = lambda: session
    app.dependency_overrides[core_dependencies.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[erp_router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[sankhya_router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[core_dependencies.get_token] = lambda: "fake"
    app.dependency_overrides[core_dependencies.get_current_user] = lambda: SimpleNamespace(
        id=uuid.uuid4(),
        perfil=SimpleNamespace(codigo="OWNER"),
    )
    _override_permission_dependencies(app)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _count_rows(session: AsyncSession, tenant_id: uuid.UUID) -> tuple[int, int]:
    sankhya_count = await session.scalar(
        select(func.count())
        .select_from(SankhyaConfig)
        .where(SankhyaConfig.tenant_id == str(tenant_id))
    )
    canonical_count = await session.scalar(
        select(func.count())
        .select_from(TenantIntegracao)
        .where(TenantIntegracao.tenant_id == str(tenant_id))
    )
    return int(sankhya_count or 0), int(canonical_count or 0)


@pytest.mark.asyncio
async def test_gets_em_tenant_vazio_retorna_estado_vazio_sem_criar_registros(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    await _seed_sankhya_provider(session)
    before = await _count_rows(session, tenant_id)

    async with _build_client(session, tenant_id) as client:
        status = await client.get("/api/v1/integracoes/erp/status")
        health = await client.get("/api/v1/integracoes/erp/health")
        jobs = await client.get("/api/v1/integracoes/erp/jobs")
        timeline = await client.get("/api/v1/integracoes/erp/timeline")
        diagnostico = await client.get("/api/v1/integracoes/erp/diagnostico")

    after = await _count_rows(session, tenant_id)

    assert before == (0, 0)
    assert after == (0, 0)
    assert status.status_code == 200
    assert status.json()["configurado"] is False
    assert status.json()["readiness"]["status"] == "NOT_CONFIGURED"
    assert status.json()["readiness"]["provider_code"] is None
    assert health.status_code == 200
    assert health.json()["status"] == "NOT_CONFIGURED"
    assert jobs.status_code == 200
    assert jobs.json() == []
    assert timeline.status_code == 200
    assert timeline.json() == []
    assert diagnostico.status_code == 200
    assert diagnostico.json()["health_atual"] == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_primeiro_save_tardio_sem_wizard_nem_implantacao_cria_config_e_integracao(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    await _seed_sankhya_provider(session)

    payload = {
        "sankhya_environment": "producao",
        "sankhya_api_base_url": "https://gateway.example/api",
        "sankhya_auth_url": "https://gateway.example/authenticate",
        "sankhya_client_id": "client-123",
        "sankhya_client_secret": "client-secret",
        "sankhya_x_token": "x-token",
        "sync_interval": 900,
    }

    async with _build_client(session, tenant_id) as client:
        status_before = await client.get("/api/v1/integracoes/erp/status")
        schema = await client.get("/api/v1/integracoes/erp/providers/sankhya/schema")
        config_before = await client.get("/api/v1/integracoes/sankhya/config")
        save_first = await client.post("/api/v1/integracoes/sankhya/config", json=payload)
        save_second = await client.post("/api/v1/integracoes/sankhya/config", json=payload)
        status_after = await client.get("/api/v1/integracoes/erp/status")
        health_after = await client.get("/api/v1/integracoes/erp/health")

    sankhya_count, canonical_count = await _count_rows(session, tenant_id)

    assert status_before.status_code == 200
    assert status_before.json()["configurado"] is False
    assert schema.status_code == 200
    assert config_before.status_code == 404
    assert save_first.status_code == 201
    assert save_second.status_code == 201
    assert sankhya_count == 1
    assert canonical_count == 1
    assert status_after.status_code == 200
    assert status_after.json()["configurado"] is True
    assert status_after.json()["readiness"]["status"] in {"PENDENTE", "ATENDIDO", "FALHOU"}
    assert health_after.status_code == 200
    assert health_after.json()["configurado"] is True


@pytest.mark.asyncio
async def test_remocao_de_erp_persistido_retorna_tenant_para_estado_sem_erp(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    await _seed_sankhya_provider(session)

    payload = {
        "sankhya_environment": "producao",
        "sankhya_api_base_url": "https://gateway.example/api",
        "sankhya_auth_url": "https://gateway.example/authenticate",
        "sankhya_client_id": "client-123",
        "sankhya_client_secret": "client-secret",
        "sankhya_x_token": "x-token",
        "sync_interval": 900,
    }

    async with _build_client(session, tenant_id) as client:
        save = await client.post("/api/v1/integracoes/sankhya/config", json=payload)
        remove = await client.delete("/api/v1/integracoes/sankhya/config")
        status_after = await client.get("/api/v1/integracoes/erp/status")
        health_after = await client.get("/api/v1/integracoes/erp/health")
        config_after = await client.get("/api/v1/integracoes/sankhya/config")

    active_canonical = await session.scalar(
        select(func.count())
        .select_from(TenantIntegracao)
        .where(TenantIntegracao.tenant_id == str(tenant_id), TenantIntegracao.deleted_at.is_(None))
    )
    removed_canonical = await session.scalar(
        select(func.count())
        .select_from(TenantIntegracao)
        .where(
            TenantIntegracao.tenant_id == str(tenant_id),
            TenantIntegracao.lifecycle_state == IntegrationStatus.REMOVED.value,
            TenantIntegracao.deleted_at.is_not(None),
        )
    )
    active_credentials = await session.scalar(
        select(func.count())
        .select_from(IntegrationCredential)
        .where(
            IntegrationCredential.tenant_id == str(tenant_id),
            IntegrationCredential.ativo.is_(True),
            IntegrationCredential.deleted_at.is_(None),
        )
    )
    active_features = await session.scalar(
        select(func.count())
        .select_from(IntegrationFeature)
        .where(
            IntegrationFeature.tenant_id == str(tenant_id),
            IntegrationFeature.deleted_at.is_(None),
        )
    )
    active_policies = await session.scalar(
        select(func.count())
        .select_from(IntegrationSyncPolicy)
        .where(
            IntegrationSyncPolicy.tenant_id == str(tenant_id),
            IntegrationSyncPolicy.deleted_at.is_(None),
        )
    )
    remaining_legacy = await session.scalar(
        select(func.count())
        .select_from(SankhyaConfig)
        .where(SankhyaConfig.tenant_id == str(tenant_id))
    )

    assert save.status_code == 201
    assert remove.status_code == 204
    assert status_after.status_code == 200
    assert status_after.json()["configurado"] is False
    assert status_after.json()["status_conexao"] == "NOT_CONFIGURED"
    assert health_after.status_code == 200
    assert health_after.json()["status"] == "NOT_CONFIGURED"
    assert config_after.status_code == 404
    assert int(active_canonical or 0) == 0
    assert int(removed_canonical or 0) == 1
    assert int(active_credentials or 0) == 0
    assert int(active_features or 0) == 0
    assert int(active_policies or 0) == 0
    assert int(remaining_legacy or 0) == 0




@pytest.mark.asyncio
async def test_drift_inverso_resolve_provider_canonico_sem_sankhya_config(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    await _seed_sankhya_provider(session)
    await SankhyaSyncService(session).criar_config(
        tenant_id=str(tenant_id),
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/authenticate",
        sankhya_client_id="client-123",
        sankhya_client_secret="client-secret",
        sankhya_x_token="x-token",
        sync_interval=900,
    )
    await session.execute(delete(SankhyaConfig).where(SankhyaConfig.tenant_id == str(tenant_id)))
    await session.commit()

    async with _build_client(session, tenant_id) as client:
        status = await client.get("/api/v1/integracoes/erp/status")
        config = await client.get("/api/v1/integracoes/sankhya/config")

    assert status.status_code == 200
    assert status.json()["configurado"] is True
    assert status.json()["provider_definition"]["provider_code"] == "sankhya"
    assert config.status_code == 404


@pytest.mark.asyncio
async def test_integracao_inativa_nao_e_confundida_com_nunca_configurada(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    await _seed_sankhya_provider(session)
    await SankhyaSyncService(session).criar_config(
        tenant_id=str(tenant_id),
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/authenticate",
        sankhya_client_id="client-123",
        sankhya_client_secret="client-secret",
        sankhya_x_token="x-token",
        sync_interval=900,
    )
    await session.execute(
        update(TenantIntegracao)
        .where(TenantIntegracao.tenant_id == str(tenant_id))
        .values(lifecycle_state=IntegrationStatus.SUSPENDED.value)
    )
    await session.commit()

    async with _build_client(session, tenant_id) as client:
        status = await client.get("/api/v1/integracoes/erp/status")

    assert status.status_code == 200
    assert status.json()["configurado"] is True
    assert status.json()["lifecycle_state"] == IntegrationStatus.SUSPENDED.value


@pytest.mark.asyncio
async def test_soft_delete_retorna_estado_vazio_sem_reutilizar_linha_removida(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    await _seed_sankhya_provider(session)
    await SankhyaSyncService(session).criar_config(
        tenant_id=str(tenant_id),
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/authenticate",
        sankhya_client_id="client-123",
        sankhya_client_secret="client-secret",
        sankhya_x_token="x-token",
        sync_interval=900,
    )
    await session.execute(delete(SankhyaConfig).where(SankhyaConfig.tenant_id == str(tenant_id)))
    await session.execute(
        update(TenantIntegracao)
        .where(TenantIntegracao.tenant_id == str(tenant_id))
        .values(deleted_at=datetime.utcnow())
    )
    await session.commit()

    before = await _count_rows(session, tenant_id)
    async with _build_client(session, tenant_id) as client:
        status = await client.get("/api/v1/integracoes/erp/status")
    after = await _count_rows(session, tenant_id)

    assert before == after
    assert status.status_code == 200
    assert status.json()["configurado"] is False
    assert status.json()["readiness"]["status"] == "NOT_CONFIGURED"
