from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import core.dependencies as core_dependencies
import integracoes.erp.router as erp_router_module
import integracoes.sankhya.routers as sankhya_router_module
from core.models import PerfilAcesso, Tenant, TenantUsuario, Usuario
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationHistory,
    IntegrationCredential,
    IntegrationFeature,
    IntegrationJob,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncMode,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
    IntegrationHealth,
)
from integracoes.schemas import ExternalRecordAssociationCreate
from integracoes.security import encrypt_integration_secret
from integracoes.services import ExternalRecordAssociationService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for table in (
            Tenant.__table__,
            Usuario.__table__,
            PerfilAcesso.__table__,
            TenantUsuario.__table__,
            MarketplaceIntegracao.__table__,
            IntegrationCredential.__table__,
            TenantIntegracao.__table__,
            IntegrationFeature.__table__,
            IntegrationSyncPolicy.__table__,
            IntegrationJob.__table__,
            ExternalRecordAssociation.__table__,
            ExternalRecordAssociationHistory.__table__,
            IntegrationHealth.__table__,
        ):
            await conn.run_sync(table.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as current:
        yield current

    await engine.dispose()


async def _seed_access(session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    session.add(
        Tenant(
            id=tenant_id,
            nome="Tenant Integracoes",
            documento=tenant_id.hex[:11],
            ativo=True,
        )
    )
    session.add(
        Usuario(
            id=user_id,
            email=f"user-{user_id.hex[:8]}@example.com",
            username=f"user_{user_id.hex[:8]}",
            nome_completo="Usuario Integracoes",
            senha_hash="hash",
            is_superuser=False,
            ativo=True,
        )
    )
    session.add(
        TenantUsuario(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            usuario_id=user_id,
            is_owner=True,
            status="ATIVO",
        )
    )
    await session.commit()


async def _seed_runtime(
    session: AsyncSession,
    *,
    tenant_id: str,
    provider_slug: str = "sankhya",
    feature_code: str = "pessoas",
    environment: str = "producao",
) -> dict[str, object]:
    provider = MarketplaceIntegracao(
        nome="Sankhya",
        slug=provider_slug,
        categoria="erp",
        provider_type="ERP",
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)

    credential = IntegrationCredential(
        tenant_id=tenant_id,
        provider_id=provider.id,
        scope_type=IntegrationScope.TENANT.value,
        segredo_criptografado=encrypt_integration_secret("segredo"),
        version_number=1,
    )
    session.add(credential)
    await session.commit()
    await session.refresh(credential)

    config = TenantIntegracao(
        tenant_id=tenant_id,
        integracao_id=provider.id,
        scope_type=IntegrationScope.TENANT.value,
        lifecycle_state=IntegrationStatus.ACTIVE.value,
        credential_ref_id=credential.id,
        connection_payload={"environment": environment},
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)

    feature = IntegrationFeature(
        tenant_id=tenant_id,
        config_id=config.id,
        provider_id=provider.id,
        codigo=feature_code,
        nome="Pessoas",
        habilitada=True,
    )
    session.add(feature)
    await session.commit()
    await session.refresh(feature)

    policy = IntegrationSyncPolicy(
        tenant_id=tenant_id,
        config_id=config.id,
        feature_id=feature.id,
        provider_id=provider.id,
        mode=IntegrationSyncMode.MANUAL.value,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)

    job = IntegrationJob(
        tenant_id=tenant_id,
        config_id=config.id,
        feature_id=feature.id,
        sync_policy_id=policy.id,
        provider_id=provider.id,
        status="SUCCESS",
        trigger_type="MANUAL",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    return {
        "provider": provider,
        "config": config,
        "feature": feature,
        "job": job,
    }


def _create_async_client(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> AsyncClient:
    app = FastAPI()
    app.include_router(sankhya_router_module.router, prefix="/api/v1/integracoes")
    app.include_router(erp_router_module.router, prefix="/api/v1/integracoes")
    app.dependency_overrides[erp_router_module.get_session] = lambda: session
    app.dependency_overrides[erp_router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[sankhya_router_module.get_session] = lambda: session
    app.dependency_overrides[sankhya_router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[core_dependencies.get_current_user] = lambda: SimpleNamespace(
        id=user_id
    )
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _seed_pending_association(
    session: AsyncSession,
    *,
    tenant_id: str,
    provider_id: int,
    config_id: int,
    feature_id: int,
    external_record_id: str = "123",
    external_entity: str = "Parceiro",
    local_entity: str = "Pessoa",
    notes: str = "aguardando validacao",
    secondary_keys: dict[str, str] | None = None,
    metadata_json: dict[str, str] | None = None,
) -> ExternalRecordAssociation:
    service = ExternalRecordAssociationService(session)
    association = await service.create_association(
        ExternalRecordAssociationCreate(
            tenant_id=tenant_id,
            provider_id=provider_id,
            config_id=config_id,
            feature_id=feature_id,
            environment="producao",
            local_entity=local_entity,
            local_record_id=None,
            external_entity=external_entity,
            external_record_id=external_record_id,
            secondary_keys=secondary_keys or {"codigo": external_record_id},
            metadata_json=metadata_json or {"feature": "pendente"},
            notes=notes,
            status="PENDING",
        )
    )
    return association


async def _seed_active_local_association(
    session: AsyncSession,
    *,
    tenant_id: str,
    provider_id: int,
    config_id: int,
    feature_id: int,
    local_record_id: str,
) -> ExternalRecordAssociation:
    service = ExternalRecordAssociationService(session)
    return await service.create_association(
        ExternalRecordAssociationCreate(
            tenant_id=tenant_id,
            provider_id=provider_id,
            config_id=config_id,
            feature_id=feature_id,
            environment="producao",
            local_entity="Pessoa",
            local_record_id=local_record_id,
            external_entity="Parceiro",
            external_record_id=str(uuid.uuid4()),
            secondary_keys={"codigo": "ativo"},
            metadata_json={"status": "ativo"},
        )
    )


@pytest.mark.asyncio
async def test_lista_pendentes_com_filtros_e_historico(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_access(session, tenant_id=tenant_id, user_id=user_id)
    runtime = await _seed_runtime(session, tenant_id=str(tenant_id))
    association = await _seed_pending_association(
        session,
        tenant_id=str(tenant_id),
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
        feature_id=runtime["feature"].id,
        external_record_id="1001",
        secondary_keys={"cpf_cnpj": "12345678901"},
        metadata_json={"origem": "erp"},
    )

    async with _create_async_client(session, tenant_id, user_id) as client:
        response = await client.get(
            "/api/v1/integracoes/erp/associacoes/pendentes",
            params={
                "provider_id": runtime["provider"].id,
                "feature_id": runtime["feature"].id,
                "entity_type": "Pessoa",
                "external_entity_type": "Parceiro",
                "environment": "producao",
                "tenant_id": str(tenant_id),
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["total_filtered"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == str(association.id)
    assert item["status"] == "PENDING"
    assert item["external_id"] == "1001"
    assert item["external_key"].endswith("|1001")
    assert item["external_payload"]["secondary_keys"]["cpf_cnpj"] == "12345678901"
    assert "origem" in item["external_payload"]["metadata_keys"]
    assert item["motivo"] == "aguardando validacao"
    assert len(item["history"]) == 1
    assert item["history"][0]["event_type"] == "CREATED"


@pytest.mark.asyncio
async def test_reconciliacao_manual_ativa_vinculo_local_explicito(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_access(session, tenant_id=tenant_id, user_id=user_id)
    runtime = await _seed_runtime(session, tenant_id=str(tenant_id))
    association = await _seed_pending_association(
        session,
        tenant_id=str(tenant_id),
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
        feature_id=runtime["feature"].id,
        external_record_id="2002",
    )

    async with _create_async_client(session, tenant_id, user_id) as client:
        response = await client.post(
            f"/api/v1/integracoes/erp/associacoes/{association.id}/reconciliar",
            json={
                "local_entity_type": "Pessoa",
                "local_entity_id": "pessoa-local-2002",
                "actor_usuario_id": str(user_id),
                "reason": "validado manualmente",
                "notes": "reconciliado",
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["local_entity_type"] == "Pessoa"
    assert body["local_entity_id"] == "pessoa-local-2002"
    assert body["motivo"] == "reconciliado"
    assert len(body["history"]) == 2
    assert body["history"][-1]["event_type"] == "RECONCILED"


@pytest.mark.asyncio
async def test_reconciliacao_manual_rejeita_conflito_local_existente(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_access(session, tenant_id=tenant_id, user_id=user_id)
    runtime = await _seed_runtime(session, tenant_id=str(tenant_id))
    await _seed_active_local_association(
        session,
        tenant_id=str(tenant_id),
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
        feature_id=runtime["feature"].id,
        local_record_id="pessoa-local-3003",
    )
    association = await _seed_pending_association(
        session,
        tenant_id=str(tenant_id),
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
        feature_id=runtime["feature"].id,
        external_record_id="3003",
    )

    async with _create_async_client(session, tenant_id, user_id) as client:
        response = await client.post(
            f"/api/v1/integracoes/erp/associacoes/{association.id}/reconciliar",
            json={
                "local_entity_type": "Pessoa",
                "local_entity_id": "pessoa-local-3003",
                "reason": "tentativa duplicada",
            },
        )

    assert response.status_code == 409, response.text
    assert "Ja existe uma associacao ativa" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rbac_rejeita_usuario_sem_vinculo_no_tenant(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    outsider_id = uuid.uuid4()
    await _seed_access(session, tenant_id=tenant_id, user_id=owner_id)
    runtime = await _seed_runtime(session, tenant_id=str(tenant_id))
    await _seed_pending_association(
        session,
        tenant_id=str(tenant_id),
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
        feature_id=runtime["feature"].id,
        external_record_id="4004",
    )

    async with _create_async_client(session, tenant_id, outsider_id) as client:
        response = await client.get("/api/v1/integracoes/erp/associacoes/pendentes")

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_tenant_isolation_retorna_apenas_registros_do_tenant_logado(session: AsyncSession) -> None:
    tenant_1_id = uuid.uuid4()
    tenant_2_id = uuid.uuid4()
    user_1_id = uuid.uuid4()
    user_2_id = uuid.uuid4()
    
    await _seed_access(session, tenant_id=tenant_1_id, user_id=user_1_id)
    await _seed_access(session, tenant_id=tenant_2_id, user_id=user_2_id)
    
    runtime_1 = await _seed_runtime(session, tenant_id=str(tenant_1_id))
    runtime_2 = await _seed_runtime(session, tenant_id=str(tenant_2_id), provider_slug="sankhya2")
    
    await _seed_pending_association(
        session,
        tenant_id=str(tenant_1_id),
        provider_id=runtime_1["provider"].id,
        config_id=runtime_1["config"].id,
        feature_id=runtime_1["feature"].id,
        external_record_id="T1-100",
        metadata_json={"secret": "should_be_hidden"},
    )
    
    await _seed_pending_association(
        session,
        tenant_id=str(tenant_2_id),
        provider_id=runtime_2["provider"].id,
        config_id=runtime_2["config"].id,
        feature_id=runtime_2["feature"].id,
        external_record_id="T2-200",
    )
    
    async with _create_async_client(session, tenant_1_id, user_1_id) as client:
        response = await client.get("/api/v1/integracoes/erp/associacoes/pendentes")
        
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["external_id"] == "T1-100"
    
    # Valida ausência de conteúdos sensíveis em raw payload
    assert "metadata_json" not in body["items"][0]["external_payload"]
    assert "secret" in body["items"][0]["external_payload"]["metadata_keys"]

