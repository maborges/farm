"""Testes unitários e de integração para Impersonação de Tenant (Acesso Assistido Backoffice/Suporte)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import Base
from core.dependencies import (
    get_session,
    get_tenant_id,
    require_grupo_access,
    require_module,
    require_tenant_permission,
)
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_impersonation import AdminImpersonation
from core.models.admin_user import AdminUser
from core.models.auth import PerfilAcesso, TenantUsuario, UnidadeProdutivaUsuario, Usuario
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.sessao import SessaoAtiva
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from core.routers.auth import router as auth_router
from core.routers.backoffice_impersonation import router as impersonation_router
from core.services.auth_service import AuthService


@pytest.fixture
async def impersonation_app(tmp_path):
    """Configura app FastAPI isolado com banco SQLite em arquivo temporário."""
    db_file = tmp_path / "test_impersonation.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        Usuario.__table__,
        AdminUser.__table__,
        Tenant.__table__,
        PerfilAcesso.__table__,
        TenantUsuario.__table__,
        UnidadeProdutiva.__table__,
        UnidadeProdutivaUsuario.__table__,
        PlanoAssinatura.__table__,
        AssinaturaTenant.__table__,
        SessaoAtiva.__table__,
        AdminImpersonation.__table__,
        AdminAuditLog.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(impersonation_router, prefix="/api/v1")

    @app.get("/api/v1/tenant-probe/read")
    async def tenant_probe_read(
        tenant_id: uuid.UUID = Depends(get_tenant_id),
        _grupo: bool = Depends(require_grupo_access()),
        _mod: bool = Depends(require_module("A1_PLANEJAMENTO")),
        _perm: bool = Depends(require_tenant_permission("agricola:safra:view")),
    ):
        return {"ok": True, "tenant_id": str(tenant_id)}

    @app.get("/api/v1/tenant-probe/uncontracted-module")
    async def tenant_probe_uncontracted(
        _mod: bool = Depends(require_module("F4_HEDGING")),
    ):
        return {"ok": True}

    @app.post("/api/v1/tenant-probe/write")
    async def tenant_probe_write(
        tenant_id: uuid.UUID = Depends(get_tenant_id),
        _perm: bool = Depends(require_tenant_permission("agricola:safra:create")),
    ):
        return {"written": True, "tenant_id": str(tenant_id)}

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    yield app, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_scenario(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Popula usuários (super_admin, suporte, financeiro) e um tenant assinante com fazenda e plano."""
    super_user_id = uuid.uuid4()
    support_user_id = uuid.uuid4()
    finance_user_id = uuid.uuid4()
    owner_user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    plano_id = uuid.uuid4()

    # Usuários globais + AdminUsers correspondentes
    u_super = Usuario(
        id=super_user_id,
        email="admin@deepfarms.com.br",
        username="superadmin",
        nome_completo="Admin Global",
        is_superuser=True,
        ativo=True,
    )
    a_super = AdminUser(
        id=super_user_id,
        email="admin@deepfarms.com.br",
        nome="Admin Global",
        senha_hash="hash",
        role="super_admin",
        ativo=True,
    )

    u_support = Usuario(
        id=support_user_id,
        email="suporte@deepfarms.com.br",
        username="analistasuporte",
        nome_completo="Analista Suporte",
        is_superuser=False,
        ativo=True,
    )
    a_support = AdminUser(
        id=support_user_id,
        email="suporte@deepfarms.com.br",
        nome="Analista Suporte",
        senha_hash="hash",
        role="suporte",
        ativo=True,
    )

    u_finance = Usuario(
        id=finance_user_id,
        email="financeiro@deepfarms.com.br",
        username="analistafin",
        nome_completo="Analista Financeiro",
        is_superuser=False,
        ativo=True,
    )
    a_finance = AdminUser(
        id=finance_user_id,
        email="financeiro@deepfarms.com.br",
        nome="Analista Financeiro",
        senha_hash="hash",
        role="financeiro",
        ativo=True,
    )

    u_owner = Usuario(
        id=owner_user_id,
        email="produtor@fazendaverde.com.br",
        username="produtorverde",
        nome_completo="João Produtor",
        is_superuser=False,
        ativo=True,
    )

    tenant = Tenant(
        id=tenant_id,
        nome="Fazenda Serra Verde",
        documento="12345678000190",
        ativo=True,
    )
    fazenda = UnidadeProdutiva(
        id=fazenda_id,
        tenant_id=tenant_id,
        nome="Unidade Matriz Serra Verde",
        ativo=True,
    )
    plano = PlanoAssinatura(
        id=plano_id,
        nome="Plano Profissional",
        plan_tier="PROFISSIONAL",
        preco_mensal=499.0,
        preco_anual=4990.0,
        max_fazendas=3,
        limite_usuarios_minimo=1,
        limite_usuarios_maximo=5,
        modulos_inclusos=["CORE", "A1_PLANEJAMENTO"],
        ativo=True,
    )
    assinatura = AssinaturaTenant(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        plano_id=plano_id,
        tipo_assinatura="TENANT",
        status="ATIVA",
        ciclo_pagamento="MENSAL",
        usuarios_contratados=1,
        data_inicio=datetime.now(timezone.utc),
    )
    tu_owner = TenantUsuario(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        usuario_id=owner_user_id,
        is_owner=True,
        status="ATIVO",
    )

    session.add_all([
        u_super,
        a_super,
        u_support,
        a_support,
        u_finance,
        a_finance,
        u_owner,
        tenant,
        fazenda,
        plano,
        assinatura,
        tu_owner,
    ])
    await session.commit()

    return {
        "super_user_id": super_user_id,
        "support_user_id": support_user_id,
        "finance_user_id": finance_user_id,
        "owner_user_id": owner_user_id,
        "tenant_id": tenant_id,
        "fazenda_id": fazenda_id,
    }


def _make_backoffice_token(
    session: AsyncSession,
    user_id: uuid.UUID,
    is_superuser: bool,
    backoffice_role: str,
    email: str,
) -> str:
    svc = AuthService(session)
    return svc.create_access_token(
        data={
            "sub": str(user_id),
            "email": email,
            "is_superuser": is_superuser,
            "role": backoffice_role,
            "backoffice_role": backoffice_role,
            "account_type": "PLATFORM_ADMIN",
            "product_scope": ["backoffice", "saas", "agro:free"],
            "session_required": False,
        }
    )


@pytest.mark.asyncio
async def test_support_and_admin_can_impersonate_without_consuming_tenant_sessions(impersonation_app):
    app, session_factory = impersonation_app

    async with session_factory() as session:
        ids = await _seed_scenario(session)
        support_token = _make_backoffice_token(
            session,
            ids["support_user_id"],
            is_superuser=False,
            backoffice_role="suporte",
            email="suporte@deepfarms.com.br",
        )
        finance_token = _make_backoffice_token(
            session,
            ids["finance_user_id"],
            is_superuser=False,
            backoffice_role="financeiro",
            email="financeiro@deepfarms.com.br",
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1:8000") as client:
        # 1. Perfil financeiro NÃO tem permissão de impersonar
        resp_forbidden = await client.post(
            "/api/v1/backoffice/impersonate/start",
            headers={"Authorization": f"Bearer {finance_token}"},
            json={
                "tenant_id": str(ids["tenant_id"]),
                "modo": "READ_ONLY",
                "motivo": "Tentativa não autorizada pelo financeiro",
                "categoria": "SUPORTE",
            },
        )
        assert resp_forbidden.status_code == 403

        # 2. Analista de suporte inicia impersonação em modo READ_ONLY
        resp_start = await client.post(
            "/api/v1/backoffice/impersonate/start",
            headers={"Authorization": f"Bearer {support_token}"},
            json={
                "tenant_id": str(ids["tenant_id"]),
                "modo": "READ_ONLY",
                "motivo": "Investigação do chamado #412 sobre planejamento de safra",
                "categoria": "SUPORTE",
            },
        )
        assert resp_start.status_code == 200
        start_data = resp_start.json()
        imp_token = start_data["access_token"]
        assert start_data["tenant"]["id"] == str(ids["tenant_id"])
        assert start_data["tenant"]["nome"] == "Fazenda Serra Verde"
        assert start_data["modo"] == "READ_ONLY"
        assert len(start_data["fazendas"]) == 1
        assert start_data["fazendas"][0]["id"] == str(ids["fazenda_id"])

        # 3. Verificar que NENHUMA SessaoAtiva foi criada para o tenant (não consome licença do cliente)
        async with session_factory() as session:
            sessoes_count = await session.scalar(
                select(func.count(SessaoAtiva.id)).where(SessaoAtiva.tenant_id == ids["tenant_id"])
            )
            assert sessoes_count == 0

            # Registro em AdminImpersonation e AdminAuditLog criados
            imp_record = await session.get(AdminImpersonation, uuid.UUID(start_data["impersonation_id"]))
            assert imp_record is not None
            assert imp_record.fim is None
            assert imp_record.tenant_id == ids["tenant_id"]

            audit_count = await session.scalar(
                select(func.count(AdminAuditLog.id)).where(
                    AdminAuditLog.acao == "TENANT_IMPERSONATION_START"
                )
            )
            assert audit_count == 1

        # 4. Consultar /auth/me com o token de impersonação: deve trazer o tenant e os dados de impersonação
        resp_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {imp_token}"},
        )
        assert resp_me.status_code == 200
        me_data = resp_me.json()
        assert len(me_data["tenants"]) == 1
        assert me_data["tenants"][0]["tenant_id"] == str(ids["tenant_id"])
        assert me_data["tenants"][0]["is_owner"] is True
        assert "A1_PLANEJAMENTO" in me_data["tenants"][0]["modulos"]
        assert me_data["impersonation"]["active"] is True
        assert me_data["impersonation"]["mode"] == "READ_ONLY"

        # 5. Leitura em rota de tenant com permissão e fazenda funciona normalmente como owner
        resp_read = await client.get(
            "/api/v1/tenant-probe/read",
            headers={
                "Authorization": f"Bearer {imp_token}",
                "x-tenant-id": str(ids["tenant_id"]),
                "x-fazenda-id": str(ids["fazenda_id"]),
            },
        )
        assert resp_read.status_code == 200
        assert resp_read.json()["tenant_id"] == str(ids["tenant_id"])

        # 6. Módulo NÃO contratado pelo assinante continua bloqueado com 402 (visão fiel ao assinante)
        resp_uncontracted = await client.get(
            "/api/v1/tenant-probe/uncontracted-module",
            headers={"Authorization": f"Bearer {imp_token}"},
        )
        assert resp_uncontracted.status_code == 402

        # 7. Escrita em modo READ_ONLY é bloqueada com 403
        resp_write_blocked = await client.post(
            "/api/v1/tenant-probe/write",
            headers={"Authorization": f"Bearer {imp_token}"},
        )
        assert resp_write_blocked.status_code == 403
        assert "Somente Leitura" in resp_write_blocked.json()["detail"]

        # 8. Alternar modo para READ_WRITE durante a sessão
        resp_mode = await client.patch(
            "/api/v1/backoffice/impersonate/mode",
            headers={"Authorization": f"Bearer {imp_token}"},
            json={"modo": "READ_WRITE", "motivo": "Liberando escrita para ajuste solicitado no chamado #412"},
        )
        assert resp_mode.status_code == 200
        rw_token = resp_mode.json()["access_token"]
        assert resp_mode.json()["modo"] == "READ_WRITE"

        # 9. Agora a escrita funciona como owner
        resp_write_ok = await client.post(
            "/api/v1/tenant-probe/write",
            headers={"Authorization": f"Bearer {rw_token}"},
        )
        assert resp_write_ok.status_code == 200
        assert resp_write_ok.json()["written"] is True

        # 10. Encerrar impersonação (/backoffice/impersonate/stop)
        resp_stop = await client.post(
            "/api/v1/backoffice/impersonate/stop",
            headers={"Authorization": f"Bearer {rw_token}"},
        )
        assert resp_stop.status_code == 200
        assert resp_stop.json()["sucesso"] is True

        # 11. Token de impersonação encerrado não pode mais operar no tenant
        resp_after_stop = await client.get(
            "/api/v1/tenant-probe/read",
            headers={"Authorization": f"Bearer {rw_token}"},
        )
        assert resp_after_stop.status_code == 401


@pytest.mark.asyncio
async def test_impersonation_when_operator_is_global_usuario_different_id_from_admin_user(impersonation_app):
    """
    Garante que se o operador autenticado for um Usuario global com is_superuser=True
    (cujo ID difere do ID da tabela admin_users), o endpoint /auth/me resolve a identidade
    com sucesso e NÃO lança 404, evitando deslogar o operador.
    """
    app, session_factory = impersonation_app

    async with session_factory() as session:
        ids = await _seed_scenario(session)

        # Cria um Usuario global superuser com ID completamente diferente de qualquer admin_users
        global_user_id = uuid.uuid4()
        user = Usuario(
            id=global_user_id,
            email="super.operador@deepfarms.com",
            username="super.operador",
            nome_completo="Super Operador",
            senha_hash="dummy_hash",
            is_superuser=True,
            ativo=True,
        )
        session.add(user)
        await session.commit()

        auth_svc = AuthService(session)
        # Token do operador com seu próprio sub de Usuario
        operator_token = auth_svc.create_access_token(
            data={
                "sub": str(global_user_id),
                "email": "super.operador@deepfarms.com",
                "is_superuser": True,
                "role": "super_admin",
                "backoffice_role": "super_admin",
                "account_type": "PLATFORM_ADMIN",
                "product_scope": ["backoffice", "saas", "agro:free"],
            }
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Iniciar impersonação
        resp_start = await client.post(
            "/api/v1/backoffice/impersonate/start",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "tenant_id": str(ids["tenant_id"]),
                "modo": "READ_ONLY",
                "motivo": "Investigação de suporte técnico por superusuário global",
            },
        )
        assert resp_start.status_code == 200
        imp_token = resp_start.json()["access_token"]

        # Consultar /auth/me: DEVE retornar 200 e trazer os dados do tenant
        resp_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {imp_token}"},
        )
        assert resp_me.status_code == 200
        data = resp_me.json()
        assert len(data["tenants"]) == 1
        assert data["tenants"][0]["tenant_id"] == str(ids["tenant_id"])
        assert data["impersonation"]["active"] is True
        assert data["impersonation"]["mode"] == "READ_ONLY"


