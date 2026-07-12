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
    ExternalRecordAssociationStatus,
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
            nome="Tenant Teste",
            documento=tenant_id.hex[:11],
            ativo=True,
        )
    )
    session.add(
        Usuario(
            id=user_id,
            email=f"user-{user_id.hex[:8]}@example.com",
            username=f"user_{user_id.hex[:8]}",
            nome_completo="Usuario Teste",
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
    feature_code: str = "associacoes",
    environment: str = "producao",
) -> dict[str, object]:
    provider = MarketplaceIntegracao(
        nome=provider_slug.capitalize(),
        slug=provider_slug,
        categoria="erp",
        provider_type="ERP",
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)

    from integracoes.security import encrypt_integration_secret
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
        nome=feature_code.capitalize(),
        habilitada=True,
    )
    session.add(feature)
    await session.commit()
    await session.refresh(feature)

    return {
        "provider": provider,
        "config": config,
        "feature": feature,
    }


def _create_async_client(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> AsyncClient:
    app = FastAPI()
    app.include_router(erp_router_module.router, prefix="/api/v1/integracoes")
    
    # Mocking dependencias base
    app.dependency_overrides[core_dependencies.get_session] = lambda: session
    app.dependency_overrides[core_dependencies.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[core_dependencies.get_token] = lambda: "fake"
    app.dependency_overrides[core_dependencies.get_current_user] = lambda: SimpleNamespace(
        id=user_id,
        perfil=SimpleNamespace(codigo="OWNER")
    )
    
    # Ignora auth para teste
    def _mock_require_permission(*args, **kwargs):
        def _dep():
            return user_id
        return _dep

    app.dependency_overrides[core_dependencies.require_tenant_permission] = _mock_require_permission

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_auditoria_http_metadata_sanitizado(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_access(session, tenant_id=tenant_id, user_id=user_id)
    runtime = await _seed_runtime(session, tenant_id=str(tenant_id))
    
    # Criar associacao pendente com dados confidenciais
    assoc = ExternalRecordAssociation(
        id=uuid.uuid4(),
        tenant_id=str(tenant_id),
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
        feature_id=runtime["feature"].id,
        environment="producao",
        local_entity="Pessoa",
        external_entity="Parceiro",
        external_record_id="999",
        status=ExternalRecordAssociationStatus.PENDING.value,
        metadata_json={
            "token": "secret_token_123",
            "campo_1": "valor_1"
        }
    )
    session.add(assoc)
    await session.commit()
    
    async with _create_async_client(session, tenant_id, user_id) as client:
        response = await client.get("/api/v1/integracoes/erp/associacoes")
        
    assert response.status_code == 200
    data = response.json()
    item = data["items"][0]
    
    # Checar se payload externo está sanitizado
    payload = item["external_payload"]
    assert "token" not in payload
    assert "metadata_json" not in payload
    assert "metadata_keys" in payload
    assert "token" in payload["metadata_keys"]
    assert "campo_1" in payload["metadata_keys"]


@pytest.mark.asyncio
async def test_contrato_paginacao(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_access(session, tenant_id=tenant_id, user_id=user_id)
    runtime = await _seed_runtime(session, tenant_id=str(tenant_id))
    
    for i in range(10):
        assoc = ExternalRecordAssociation(
            id=uuid.uuid4(),
            tenant_id=str(tenant_id),
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            environment="producao",
            local_entity="Pessoa",
            external_entity="Parceiro",
            external_record_id=str(100 + i),
            status=ExternalRecordAssociationStatus.PENDING.value,
        )
        session.add(assoc)
    await session.commit()
    
    async with _create_async_client(session, tenant_id, user_id) as client:
        # Check defaults
        response = await client.get("/api/v1/integracoes/erp/associacoes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["total_filtered"] == 10
        assert len(data["items"]) == 10
        assert data["limit"] == 50
        assert data["offset"] == 0
        
        # Check custom limit and offset
        response = await client.get("/api/v1/integracoes/erp/associacoes?limit=5&offset=2")
        data = response.json()
        assert data["total"] == 10
        assert data["total_filtered"] == 10
        assert len(data["items"]) == 5
        assert data["limit"] == 5
        assert data["offset"] == 2
        

@pytest.mark.asyncio
async def test_isolamento_tenant(session: AsyncSession) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    user_a = uuid.uuid4()
    
    await _seed_access(session, tenant_id=tenant_a, user_id=user_a)
    await _seed_access(session, tenant_id=tenant_b, user_id=uuid.uuid4())
    
    runtime_a = await _seed_runtime(session, tenant_id=str(tenant_a))
    runtime_b = await _seed_runtime(session, tenant_id=str(tenant_b), provider_slug="sankhya_b")
    
    # Add assoc to A
    assoc_a = ExternalRecordAssociation(
        id=uuid.uuid4(),
        tenant_id=str(tenant_a),
        provider_id=runtime_a["provider"].id,
        config_id=runtime_a["config"].id,
        feature_id=runtime_a["feature"].id,
        environment="producao",
        local_entity="Pessoa",
        external_entity="Parceiro",
        external_record_id="A-100",
        status=ExternalRecordAssociationStatus.PENDING.value,
    )
    session.add(assoc_a)
    
    # Add assoc to B
    assoc_b = ExternalRecordAssociation(
        id=uuid.uuid4(),
        tenant_id=str(tenant_b),
        provider_id=runtime_b["provider"].id,
        config_id=runtime_b["config"].id,
        feature_id=runtime_b["feature"].id,
        environment="producao",
        local_entity="Pessoa",
        external_entity="Parceiro",
        external_record_id="B-200",
        status=ExternalRecordAssociationStatus.PENDING.value,
    )
    session.add(assoc_b)
    await session.commit()
    
    async with _create_async_client(session, tenant_a, user_a) as client:
        # Acessa A - só lista as de A
        response = await client.get("/api/v1/integracoes/erp/associacoes")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["external_id"] == "A-100"
        
        # Tenta reconciliar B via A - deve dar erro 404/403
        reconcile_response = await client.post(
            f"/api/v1/integracoes/erp/associacoes/{assoc_b.id}/reconciliar",
            json={
                "local_entity_type": "Pessoa",
                "local_entity_id": "1",
                "reason": "abc"
            }
        )
        assert reconcile_response.status_code == 404
        
        # Testar o resumo apenas do A
        resumo_response = await client.get("/api/v1/integracoes/erp/associacoes/resumo")
        assert resumo_response.status_code == 200
        resumo = resumo_response.json()
        assert resumo["PENDING"] == 1


@pytest.mark.asyncio
async def test_status_conflito_nao_reconcilia(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_access(session, tenant_id=tenant_id, user_id=user_id)
    runtime = await _seed_runtime(session, tenant_id=str(tenant_id))
    
    assoc = ExternalRecordAssociation(
        id=uuid.uuid4(),
        tenant_id=str(tenant_id),
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
        feature_id=runtime["feature"].id,
        environment="producao",
        local_entity="Pessoa",
        external_entity="Parceiro",
        external_record_id="CONFLICT_1",
        status=ExternalRecordAssociationStatus.CONFLICT.value,
    )
    session.add(assoc)
    await session.commit()
    
    async with _create_async_client(session, tenant_id, user_id) as client:
        reconcile_response = await client.post(
            f"/api/v1/integracoes/erp/associacoes/{assoc.id}/reconciliar",
            json={
                "local_entity_type": "Pessoa",
                "local_entity_id": "1",
                "reason": "abc"
            }
        )
        assert reconcile_response.status_code == 409


@pytest.mark.asyncio
async def test_status_pending_para_active(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_access(session, tenant_id=tenant_id, user_id=user_id)
    runtime = await _seed_runtime(session, tenant_id=str(tenant_id))
    
    assoc = ExternalRecordAssociation(
        id=uuid.uuid4(),
        tenant_id=str(tenant_id),
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
        feature_id=runtime["feature"].id,
        environment="producao",
        local_entity="Pessoa",
        external_entity="Parceiro",
        external_record_id="PENDING_1",
        status=ExternalRecordAssociationStatus.PENDING.value,
    )
    session.add(assoc)
    await session.commit()
    
    async with _create_async_client(session, tenant_id, user_id) as client:
        reconcile_response = await client.post(
            f"/api/v1/integracoes/erp/associacoes/{assoc.id}/reconciliar",
            json={
                "local_entity_type": "Pessoa",
                "local_entity_id": "local_123",
                "reason": "validado",
                "notes": "notado"
            }
        )
        assert reconcile_response.status_code == 200
        data = reconcile_response.json()
        assert data["status"] == "ACTIVE"
        assert len(data["history"]) == 1
        assert data["history"][0]["event_type"] == "RECONCILED"
        assert data["history"][0]["reason"] == "validado"
        
        # Testar active não pode ser reconciliada novamente
        reconcile_again = await client.post(
            f"/api/v1/integracoes/erp/associacoes/{assoc.id}/reconciliar",
            json={
                "local_entity_type": "Pessoa",
                "local_entity_id": "local_123",
                "reason": "validado novamente"
            }
        )
        assert reconcile_again.status_code == 409

