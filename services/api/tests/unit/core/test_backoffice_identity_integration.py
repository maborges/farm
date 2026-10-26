"""Testes de integração do Backoffice com a Identidade Global Unificada (AGRO-ADMIN-01B2B).

Valida:
1. Listagem de usuários com account_type ("INDIVIDUAL_FREE", "COMMERCIAL", "PLATFORM_ADMIN") e produtos contratados.
2. Filtro por tipo de conta (all, free, commercial) e busca textual.
3. Métricas no dashboard administrativo (usuarios_gratuitos_total, usuarios_comerciais_total).
4. Invalidação imediata de sessões ativas ao bloquear usuário (ativo=False).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.dependencies import get_session, get_current_admin
from core.models.auth import Usuario, TenantUsuario, PerfilAcesso
from core.models.tenant import Tenant
from core.models.sessao import SessaoAtiva
from core.models.billing import PlanoAssinatura, AssinaturaTenant
from core.models.admin_audit_log import AdminAuditLog
from core.routers.backoffice import router as backoffice_router


@pytest.fixture
async def setup_backoffice_app(tmp_path):
    db_file = tmp_path / "test_backoffice_identity.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        Usuario.__table__,
        Tenant.__table__,
        TenantUsuario.__table__,
        SessaoAtiva.__table__,
        PlanoAssinatura.__table__,
        AssinaturaTenant.__table__,
        AdminAuditLog.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(backoffice_router, prefix="/api/v1")

    async def override_get_session():
        async with session_factory() as session:
            yield session

    # Mock admin para permitir acesso sem passar por auth completa nos testes unitários
    mock_admin_user = Usuario(
        id=uuid.uuid4(),
        email="admin@deepfarms.com",
        username="superadmin",
        is_superuser=True,
        ativo=True,
    )

    async def override_get_current_admin():
        return mock_admin_user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    yield app, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_backoffice_users_list_and_filters(setup_backoffice_app):
    app, session_factory = setup_backoffice_app

    user_free_id = uuid.uuid4()
    user_comm_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    async with session_factory() as session:
        # Usuário Gratuito
        u_free = Usuario(
            id=user_free_id,
            email="produtor.free@agro.com.br",
            username="produtorfree",
            nome_completo="Produtor Gratuito",
            is_superuser=False,
            ativo=True,
        )
        # Tenant e Usuário Comercial
        tenant = Tenant(
            id=tenant_id,
            nome="Fazenda Santa Fé",
            documento="12345678000199",
            ativo=True,
        )
        u_comm = Usuario(
            id=user_comm_id,
            email="gestor.comercial@fazenda.com.br",
            username="gestorcomercial",
            nome_completo="Gestor Comercial",
            is_superuser=False,
            ativo=True,
        )
        tu = TenantUsuario(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            usuario_id=user_comm_id,
            is_owner=True,
        )
        session.add_all([u_free, tenant, u_comm, tu])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Listagem completa (sem filtros)
        resp_all = await client.get("/api/v1/backoffice/users")
        assert resp_all.status_code == 200
        data_all = resp_all.json()
        assert len(data_all) == 2

        free_item = next(item for item in data_all if item["id"] == str(user_free_id))
        comm_item = next(item for item in data_all if item["id"] == str(user_comm_id))

        assert free_item["account_type"] == "INDIVIDUAL_FREE"
        assert free_item["produtos"] == ["DeepFarms Agro Gratuito"]
        assert free_item["tenants"] == []

        assert comm_item["account_type"] == "COMMERCIAL"
        assert comm_item["produtos"] == ["SaaS Comercial", "DeepFarms Agro"]
        assert comm_item["tenants"] == ["Fazenda Santa Fé"]
        assert comm_item["is_owner"] is True

        # 2. Filtro account_type=free
        resp_free = await client.get("/api/v1/backoffice/users?account_type=free")
        assert resp_free.status_code == 200
        data_free = resp_free.json()
        assert len(data_free) == 1
        assert data_free[0]["id"] == str(user_free_id)

        # 3. Filtro account_type=commercial
        resp_comm = await client.get("/api/v1/backoffice/users?account_type=commercial")
        assert resp_comm.status_code == 200
        data_comm = resp_comm.json()
        assert len(data_comm) == 1
        assert data_comm[0]["id"] == str(user_comm_id)

        # 4. Busca textual
        resp_search = await client.get("/api/v1/backoffice/users?search=produtor.free")
        assert resp_search.status_code == 200
        assert len(resp_search.json()) == 1
        assert resp_search.json()[0]["id"] == str(user_free_id)


@pytest.mark.asyncio
async def test_backoffice_stats_metrics(setup_backoffice_app):
    app, session_factory = setup_backoffice_app

    async with session_factory() as session:
        # 1 Gratuito, 1 Comercial
        u_free = Usuario(
            id=uuid.uuid4(),
            email="free1@agro.com.br",
            username="free1",
            nome_completo="Free One",
            is_superuser=False,
            ativo=True,
        )
        tenant = Tenant(id=uuid.uuid4(), nome="Fazenda Modelo", documento="0001", ativo=True)
        u_comm = Usuario(
            id=uuid.uuid4(),
            email="comm1@agro.com.br",
            username="comm1",
            nome_completo="Comm One",
            is_superuser=False,
            ativo=True,
        )
        tu = TenantUsuario(id=uuid.uuid4(), tenant_id=tenant.id, usuario_id=u_comm.id, is_owner=True)
        session.add_all([u_free, tenant, u_comm, tu])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/backoffice/dashboard/stats")
        assert resp.status_code == 200
        stats = resp.json()["resumo"]
        assert stats["usuarios_total"] == 2
        assert stats["usuarios_gratuitos_total"] == 1
        assert stats["usuarios_comerciais_total"] == 1


@pytest.mark.asyncio
async def test_toggle_user_status_revokes_sessions(setup_backoffice_app):
    app, session_factory = setup_backoffice_app

    target_user_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with session_factory() as session:
        user = Usuario(
            id=target_user_id,
            email="bloqueavel@agro.com.br",
            username="bloqueavel",
            nome_completo="Usuario Bloqueável",
            is_superuser=False,
            ativo=True,
        )
        sessao = SessaoAtiva(
            id=session_id,
            usuario_id=target_user_id,
            tenant_id=None,
            token_hash="hash_teste_sessao_12345",
            status="ATIVA",
            expira_em=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        session.add_all([user, sessao])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Desativa o usuário
        resp_toggle = await client.post(f"/api/v1/backoffice/users/{target_user_id}/toggle-status")
        assert resp_toggle.status_code == 200
        assert resp_toggle.json()["novo_status"] is False

    # Verifica se a sessão foi imediatamente encerrada
    async with session_factory() as session:
        updated_session = await session.get(SessaoAtiva, session_id)
        assert updated_session is not None
        assert updated_session.status == "ENCERRADA"
