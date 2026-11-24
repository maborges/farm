"""Testes unitários e de integração para Perfil Demonstração, CRM, LGPD e Prorrogação."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.constants import (
    DEMO_CRM_STAGE_NAME,
    DEMO_EXTENSION_TICKET_CATEGORY,
    DEMO_PROFILE_NAME,
    DEMO_TENANT_CANONICAL_NAME,
    TenantRoles,
)
from core.database import Base, apply_tenant_context_after_begin
from core.dependencies import get_session, get_tenant_id, require_tenant_permission
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_impersonation import AdminImpersonation
from core.models.admin_user import AdminUser
from core.models.auth import (
    ConviteAcesso,
    PerfilAcesso,
    TenantUsuario,
    TentativaLogin,
    UnidadeProdutivaUsuario,
    Usuario,
)
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.configuration import ConfiguracaoSaaS
from core.models.crm import AtividadeCRM, LeadCRM, PipelineEstagio
from core.models.sessao import SessaoAtiva
from core.models.support import ChamadoSuporte, MensagemChamado
from core.models.tenant import Tenant
from core.models.tenant_config import ConfiguracaoTenant
from core.models.unidade_produtiva import UnidadeProdutiva
from core.routers import backoffice_tenants as backoffice_tenants_module
from core.routers import support_ws as support_ws_module
from core.routers.auth import router as auth_router
from core.routers.backoffice import router as backoffice_router
from core.routers.backoffice_tenants import router as backoffice_tenants_router
from core.routers.configuration import router as configuration_router
from core.routers.onboarding import router as onboarding_router
from core.routers.support import router as support_router
from core.routers.team import router as team_router
from core.services.auth_service import AuthService, hash_password
from core.services.demo_access_service import DemoLeadSyncInput, sync_demo_lead_to_crm
from core.services.demo_config_service import invalidate_demo_config_cache
from core.services.email_service import email_service


@pytest.fixture
async def demo_app(tmp_path, monkeypatch):
    """Configura app FastAPI isolado em SQLite temporário com rotas e probes de demonstração."""
    db_file = tmp_path / "test_demo_readonly.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        Usuario.__table__,
        AdminUser.__table__,
        Tenant.__table__,
        ConfiguracaoSaaS.__table__,
        ConfiguracaoTenant.__table__,
        PerfilAcesso.__table__,
        TenantUsuario.__table__,
        TentativaLogin.__table__,
        ConviteAcesso.__table__,
        UnidadeProdutiva.__table__,
        UnidadeProdutivaUsuario.__table__,
        PlanoAssinatura.__table__,
        AssinaturaTenant.__table__,
        SessaoAtiva.__table__,
        AdminImpersonation.__table__,
        AdminAuditLog.__table__,
        ChamadoSuporte.__table__,
        MensagemChamado.__table__,
        PipelineEstagio.__table__,
        LeadCRM.__table__,
        AtividadeCRM.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(email_service, "send_invite", AsyncMock(return_value=True))
    monkeypatch.setattr(email_service, "send_registration_confirmation", AsyncMock(return_value=True))
    monkeypatch.setattr(email_service, "send_activation_link", AsyncMock(return_value=True))
    monkeypatch.setattr(backoffice_tenants_module, "async_session_maker", session_factory)
    monkeypatch.setattr(support_ws_module, "async_session_maker", session_factory)

    invalidate_demo_config_cache()

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(team_router, prefix="/api/v1")
    app.include_router(onboarding_router, prefix="/api/v1")
    app.include_router(support_router, prefix="/api/v1")
    app.include_router(backoffice_router, prefix="/api/v1")
    app.include_router(backoffice_tenants_router, prefix="/api/v1")
    app.include_router(configuration_router, prefix="/api/v1")

    @app.get("/api/v1/demo-probe/read")
    async def demo_probe_read(
        tenant_id: uuid.UUID = Depends(get_tenant_id),
        session: AsyncSession = Depends(get_session),
        _perm: bool = Depends(require_tenant_permission("agricola:safras:view")),
    ):
        return {
            "ok": True,
            "tenant_id": str(tenant_id),
            "read_only_tx": bool(session.info.get("read_only_transaction")),
        }

    @app.post("/api/v1/demo-probe/unprotected-write")
    async def demo_probe_unprotected_post(tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"written": True, "tenant_id": str(tenant_id)}

    @app.put("/api/v1/demo-probe/unprotected-write")
    async def demo_probe_unprotected_put(tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"written": True, "tenant_id": str(tenant_id)}

    @app.patch("/api/v1/demo-probe/unprotected-write")
    async def demo_probe_unprotected_patch(tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"written": True, "tenant_id": str(tenant_id)}

    @app.delete("/api/v1/demo-probe/unprotected-write")
    async def demo_probe_unprotected_delete(tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"written": True, "tenant_id": str(tenant_id)}

    @app.get("/api/v1/cadastros/pessoas/{pessoa_id}/pii")
    async def demo_probe_pii(pessoa_id: str, tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"pessoa_id": pessoa_id, "tenant_id": str(tenant_id)}

    @app.get("/api/v1/ia/assistente")
    async def demo_probe_ia(tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"tenant_id": str(tenant_id)}

    @app.get("/api/v1/campo/sync")
    async def demo_probe_campo(tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"tenant_id": str(tenant_id)}

    @app.get("/api/v1/audit-log")
    async def demo_probe_audit_log(tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"tenant_id": str(tenant_id)}

    @app.get("/api/v1/sessions/team")
    async def demo_probe_sessions_team(tenant_id: uuid.UUID = Depends(get_tenant_id)):
        return {"tenant_id": str(tenant_id)}

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    yield app, session_factory

    invalidate_demo_config_cache()
    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_demo_environment(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Cria admins (admin/comercial/suporte), tenant demo Produtor DeepFarms e tenant comercial."""
    admin_id = uuid.uuid4()
    comercial_id = uuid.uuid4()
    suporte_id = uuid.uuid4()
    demo_owner_id = uuid.uuid4()
    comm_owner_id = uuid.uuid4()

    demo_tenant_id = uuid.uuid4()
    comm_tenant_id = uuid.uuid4()
    plano_id = uuid.uuid4()
    faz_demo_1 = uuid.uuid4()
    faz_demo_2 = uuid.uuid4()
    faz_demo_inativa = uuid.uuid4()
    faz_comm_1 = uuid.uuid4()
    perfil_gestor_id = uuid.uuid4()

    pwd_hash = hash_password("SenhaForte123!")

    session.add_all([
        Usuario(
            id=admin_id,
            email="admin@deepfarms.com.br",
            username="admin_global",
            nome_completo="Admin Global",
            senha_hash=pwd_hash,
            is_superuser=True,
            ativo=True,
        ),
        AdminUser(
            id=admin_id,
            email="admin@deepfarms.com.br",
            nome="Admin Global",
            senha_hash=pwd_hash,
            role="super_admin",
            ativo=True,
        ),
        Usuario(
            id=comercial_id,
            email="comercial@deepfarms.com.br",
            username="comercial_user",
            nome_completo="Equipe Comercial",
            senha_hash=pwd_hash,
            is_superuser=False,
            ativo=True,
        ),
        AdminUser(
            id=comercial_id,
            email="comercial@deepfarms.com.br",
            nome="Equipe Comercial",
            senha_hash=pwd_hash,
            role="comercial",
            ativo=True,
        ),
        Usuario(
            id=suporte_id,
            email="suporte@deepfarms.com.br",
            username="suporte_user",
            nome_completo="Analista Suporte",
            senha_hash=pwd_hash,
            is_superuser=False,
            ativo=True,
        ),
        AdminUser(
            id=suporte_id,
            email="suporte@deepfarms.com.br",
            nome="Analista Suporte",
            senha_hash=pwd_hash,
            role="suporte",
            ativo=True,
        ),
        Usuario(
            id=demo_owner_id,
            email="dono.demo@deepfarms.com.br",
            username="dono_demo",
            nome_completo="Gestor Demo Interno",
            senha_hash=pwd_hash,
            is_superuser=False,
            ativo=True,
        ),
        Usuario(
            id=comm_owner_id,
            email="dono.comercial@fazenda.com.br",
            username="dono_comercial",
            nome_completo="Dono Fazenda Comercial",
            senha_hash=pwd_hash,
            is_superuser=False,
            ativo=True,
        ),
        PlanoAssinatura(
            id=plano_id,
            nome="Plano Enterprise",
            plan_tier="ENTERPRISE",
            preco_mensal=999.0,
            preco_anual=9990.0,
            max_fazendas=10,
            limite_usuarios_minimo=1,
            limite_usuarios_maximo=20,
            modulos_inclusos=["CORE", "A1_PLANEJAMENTO"],
            ativo=True,
        ),
        Tenant(
            id=demo_tenant_id,
            nome=DEMO_TENANT_CANONICAL_NAME,
            documento="11111111000111",
            ativo=True,
            is_demo=True,
            demo_max_sessoes_simultaneas=10,
        ),
        Tenant(
            id=comm_tenant_id,
            nome="Fazenda Boa Esperança",
            documento="22222222000122",
            ativo=True,
            is_demo=False,
        ),
        AssinaturaTenant(
            id=uuid.uuid4(),
            tenant_id=demo_tenant_id,
            plano_id=plano_id,
            tipo_assinatura="TENANT",
            status="ATIVA",
            ciclo_pagamento="MENSAL",
            usuarios_contratados=10,
            data_inicio=datetime.now(timezone.utc),
        ),
        AssinaturaTenant(
            id=uuid.uuid4(),
            tenant_id=comm_tenant_id,
            plano_id=plano_id,
            tipo_assinatura="TENANT",
            status="ATIVA",
            ciclo_pagamento="MENSAL",
            usuarios_contratados=5,
            data_inicio=datetime.now(timezone.utc),
        ),
        UnidadeProdutiva(id=faz_demo_1, tenant_id=demo_tenant_id, nome="Fazenda Modelo Norte", ativo=True),
        UnidadeProdutiva(id=faz_demo_2, tenant_id=demo_tenant_id, nome="Fazenda Modelo Sul", ativo=True),
        UnidadeProdutiva(id=faz_demo_inativa, tenant_id=demo_tenant_id, nome="Fazenda Inativa", ativo=False),
        UnidadeProdutiva(id=faz_comm_1, tenant_id=comm_tenant_id, nome="Matriz Comercial", ativo=True),
        PerfilAcesso(
            id=perfil_gestor_id,
            tenant_id=None,
            nome="Gerente",
            is_custom=False,
            is_read_only=False,
            is_demo_profile=False,
            permissoes={},
        ),
        TenantUsuario(
            id=uuid.uuid4(),
            tenant_id=demo_tenant_id,
            usuario_id=demo_owner_id,
            is_owner=True,
            perfil_id=perfil_gestor_id,
            status="ATIVO",
        ),
        TenantUsuario(
            id=uuid.uuid4(),
            tenant_id=comm_tenant_id,
            usuario_id=comm_owner_id,
            is_owner=True,
            perfil_id=perfil_gestor_id,
            status="ATIVO",
        ),
    ])
    await session.commit()

    return {
        "admin_id": admin_id,
        "comercial_id": comercial_id,
        "suporte_id": suporte_id,
        "demo_owner_id": demo_owner_id,
        "comm_owner_id": comm_owner_id,
        "demo_tenant_id": demo_tenant_id,
        "comm_tenant_id": comm_tenant_id,
        "faz_demo_1": faz_demo_1,
        "faz_demo_2": faz_demo_2,
        "faz_demo_inativa": faz_demo_inativa,
        "faz_comm_1": faz_comm_1,
        "perfil_gestor_id": perfil_gestor_id,
    }


def _make_tenant_token(
    session: AsyncSession,
    user_id: uuid.UUID,
    email: str,
    tenant_id: uuid.UUID,
    role: str,
    *,
    is_read_only: bool = False,
    is_demo_visitor: bool = False,
    demo_expired: bool = False,
) -> str:
    svc = AuthService(session)
    return svc.create_access_token({
        "sub": str(user_id),
        "email": email,
        "tenant_id": str(tenant_id),
        "role": role,
        "account_type": "COMMERCIAL",
        "product_scope": ["saas", "agro:free"],
        "session_required": False,
        "is_read_only": is_read_only,
        "is_demo_visitor": is_demo_visitor,
        "demo_expired": demo_expired,
    })


def _make_backoffice_token(
    session: AsyncSession,
    user_id: uuid.UUID,
    email: str,
    role: str,
    *,
    is_superuser: bool = False,
) -> str:
    svc = AuthService(session)
    return svc.create_access_token({
        "sub": str(user_id),
        "email": email,
        "is_superuser": is_superuser,
        "is_admin_portal": True,
        "role": role,
        "backoffice_role": role,
        "account_type": "PLATFORM_ADMIN",
        "product_scope": ["backoffice", "saas", "agro:free"],
        "session_required": False,
    })


@pytest.mark.asyncio
async def test_demo_invite_lock_and_normal_tenant_preserved(demo_app):
    """Demo tenant trava convite em Demonstração + fazendas ativas; tenant comercial segue normal."""
    app, session_factory = demo_app
    async with session_factory() as session:
        ids = await _seed_demo_environment(session)
        demo_owner_token = _make_tenant_token(
            session, ids["demo_owner_id"], "dono.demo@deepfarms.com.br", ids["demo_tenant_id"], TenantRoles.OWNER
        )
        comm_owner_token = _make_tenant_token(
            session, ids["comm_owner_id"], "dono.comercial@fazenda.com.br", ids["comm_tenant_id"], TenantRoles.OWNER
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Tenant demo garante/retorna perfil Demonstração
        resp_demo_roles = await client.get(
            "/api/v1/team/roles",
            headers={"Authorization": f"Bearer {demo_owner_token}"},
        )
        assert resp_demo_roles.status_code == 200
        demo_roles = resp_demo_roles.json()
        demo_profile = next((r for r in demo_roles if r["nome"] == DEMO_PROFILE_NAME), None)
        assert demo_profile is not None
        assert demo_profile["is_read_only"] is True
        assert demo_profile["is_demo_profile"] is True

        # 2. Tenant comercial NÃO recebe perfil Demonstração na lista
        resp_comm_roles = await client.get(
            "/api/v1/team/roles",
            headers={"Authorization": f"Bearer {comm_owner_token}"},
        )
        assert resp_comm_roles.status_code == 200
        assert all(not r["is_demo_profile"] for r in resp_comm_roles.json())

        # 3. Convite no tenant demo ignora perfil arbitrário / validade / fazendas parciais
        resp_demo_invite = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {demo_owner_token}"},
            json={
                "email": "visitante1@agro.com.br",
                "perfil_id": str(ids["perfil_gestor_id"]),
                "fazendas_ids": [str(ids["faz_demo_1"])],
                "data_validade_acesso": "2030-01-01",
            },
        )
        assert resp_demo_invite.status_code == 201
        demo_invite_token = resp_demo_invite.json()["token"]

        # 4. Convite no tenant comercial respeita perfil Gestor e fazenda escolhida
        resp_comm_invite = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {comm_owner_token}"},
            json={
                "email": "membro@comercial.com.br",
                "perfil_id": str(ids["perfil_gestor_id"]),
                "fazendas_ids": [str(ids["faz_comm_1"])],
            },
        )
        assert resp_comm_invite.status_code == 201
        comm_invite_token = resp_comm_invite.json()["token"]

    async with session_factory() as session:
        conv_demo = (
            await session.execute(select(ConviteAcesso).where(ConviteAcesso.token_convite == demo_invite_token))
        ).scalar_one()
        assert str(conv_demo.perfil_id) == demo_profile["id"]
        assert conv_demo.data_validade_acesso is None
        assert set(conv_demo.unidades_produtivas_ids) == {str(ids["faz_demo_1"]), str(ids["faz_demo_2"])}

        conv_comm = (
            await session.execute(select(ConviteAcesso).where(ConviteAcesso.token_convite == comm_invite_token))
        ).scalar_one()
        assert conv_comm.perfil_id == ids["perfil_gestor_id"]
        assert conv_comm.unidades_produtivas_ids == [str(ids["faz_comm_1"])]


@pytest.mark.asyncio
async def test_demo_onboarding_registration_and_crm_sync(demo_app):
    """Registro pelo convite demo define validade de 15 dias e cria/atualiza lead no CRM."""
    app, session_factory = demo_app
    async with session_factory() as session:
        ids = await _seed_demo_environment(session)
        demo_owner_token = _make_tenant_token(
            session, ids["demo_owner_id"], "dono.demo@deepfarms.com.br", ids["demo_tenant_id"], TenantRoles.OWNER
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        inv1 = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {demo_owner_token}"},
            json={"email": "lead1@fazenda.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
        )
        token1 = inv1.json()["token"]

        inv2 = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {demo_owner_token}"},
            json={"email": "lead2@fazenda.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
        )
        token2 = inv2.json()["token"]

        details = await client.get(f"/api/v1/onboarding/convites/{token1}")
        assert details.status_code == 200
        assert details.json()["is_demo"] is True

        # Registro COM telefone e empresa opcionais
        reg1 = await client.post(
            "/api/v1/onboarding/convites/registrar",
            json={
                "token": token1,
                "senha": "MinhaSenha123!",
                "nome_completo": "Visitante Um",
                "telefone": "(43) 99999-1111",
                "empresa": "Fazenda Esperança Demo",
            },
        )
        assert reg1.status_code == 200
        assert "access_token" in reg1.json()

        # Registro SEM telefone e empresa opcionais
        reg2 = await client.post(
            "/api/v1/onboarding/convites/registrar",
            json={
                "token": token2,
                "senha": "MinhaSenha123!",
                "nome_completo": "Visitante Dois",
            },
        )
        assert reg2.status_code == 200

    async with session_factory() as session:
        expected_expiry = date.today() + timedelta(days=15)
        u1 = (await session.execute(select(Usuario).where(Usuario.email == "lead1@fazenda.com.br"))).scalar_one()
        tu1 = (
            await session.execute(
                select(TenantUsuario).where(
                    TenantUsuario.usuario_id == u1.id,
                    TenantUsuario.tenant_id == ids["demo_tenant_id"],
                )
            )
        ).scalar_one()
        assert tu1.data_validade_acesso == expected_expiry

        stage = (
            await session.execute(select(PipelineEstagio).where(PipelineEstagio.nome == DEMO_CRM_STAGE_NAME))
        ).scalar_one()
        lead1 = (await session.execute(select(LeadCRM).where(LeadCRM.email == "lead1@fazenda.com.br"))).scalar_one()
        assert lead1.estagio_id == stage.id
        assert lead1.telefone == "(43) 99999-1111"
        assert lead1.empresa == "Fazenda Esperança Demo"

        lead2 = (await session.execute(select(LeadCRM).where(LeadCRM.email == "lead2@fazenda.com.br"))).scalar_one()
        assert lead2.estagio_id == stage.id
        assert lead2.telefone is None

        atividades = (
            await session.execute(select(AtividadeCRM).where(AtividadeCRM.lead_id == lead1.id))
        ).scalars().all()
        assert len(atividades) >= 1

        # Re-sincronização preserva dados existentes sem duplicar lead e preenche campos vazios
        await sync_demo_lead_to_crm(
            session,
            DemoLeadSyncInput(
                nome="Visitante Um Atualizado",
                email="lead1@fazenda.com.br",
                tenant_id=ids["demo_tenant_id"],
                telefone="(43) 98888-0000",
                empresa="Agro Nova",
            ),
        )
        await sync_demo_lead_to_crm(
            session,
            DemoLeadSyncInput(
                nome="Visitante Dois",
                email="lead2@fazenda.com.br",
                tenant_id=ids["demo_tenant_id"],
                telefone="(43) 97777-2222",
                empresa="Sítio Complementado",
            ),
        )
        await session.commit()
        leads_dup = (
            await session.execute(select(LeadCRM).where(LeadCRM.email == "lead1@fazenda.com.br"))
        ).scalars().all()
        assert len(leads_dup) == 1
        assert leads_dup[0].telefone == "(43) 99999-1111"

        lead2_updated = (
            await session.execute(select(LeadCRM).where(LeadCRM.email == "lead2@fazenda.com.br"))
        ).scalar_one()
        assert lead2_updated.telefone == "(43) 97777-2222"
        assert lead2_updated.empresa == "Sítio Complementado"


@pytest.mark.asyncio
async def test_readonly_defense_in_depth_http_and_postgres_tx(demo_app):
    """Perfil Demonstração bloqueia qualquer escrita HTTP e ativa transação PostgreSQL READ ONLY."""
    app, session_factory = demo_app
    async with session_factory() as session:
        ids = await _seed_demo_environment(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with session_factory() as session:
            owner_tok = _make_tenant_token(
                session, ids["demo_owner_id"], "dono.demo@deepfarms.com.br", ids["demo_tenant_id"], TenantRoles.OWNER
            )
        inv = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {owner_tok}"},
            json={"email": "leitura@agro.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
        )
        reg = await client.post(
            "/api/v1/onboarding/convites/registrar",
            json={"token": inv.json()["token"], "senha": "MinhaSenha123!", "nome_completo": "Visitante Leitura"},
        )
        visitor_token = reg.json()["access_token"]

        read_resp = await client.get(
            "/api/v1/demo-probe/read",
            headers={"Authorization": f"Bearer {visitor_token}"},
        )
        assert read_resp.status_code == 200
        assert read_resp.json()["read_only_tx"] is True

        for method in ("post", "put", "patch", "delete"):
            write_resp = await getattr(client, method)(
                "/api/v1/demo-probe/unprotected-write",
                headers={"Authorization": f"Bearer {visitor_token}"},
            )
            assert write_resp.status_code == 403
            assert write_resp.headers.get("X-Error-Code") == "READ_ONLY_PROFILE"

    # Verifica geração de SET LOCAL TRANSACTION READ ONLY quando dialeto é PostgreSQL
    executed_sql: list[str] = []
    mock_conn = MagicMock()
    mock_conn.dialect.name = "postgresql"
    mock_conn.execute = lambda stmt: executed_sql.append(str(stmt))
    mock_session = MagicMock()
    mock_session.info = {"read_only_transaction": True}

    apply_tenant_context_after_begin(mock_session, None, mock_conn)
    assert any("SET LOCAL TRANSACTION READ ONLY" in sql for sql in executed_sql)


@pytest.mark.asyncio
async def test_lgpd_restricted_paths_and_cross_visitor_support_isolation(demo_app):
    """Bloqueia rotas sensíveis LGPD e isola chamados/WS entre visitantes do mesmo tenant demo."""
    app, session_factory = demo_app
    async with session_factory() as session:
        ids = await _seed_demo_environment(session)
        owner_tok = _make_tenant_token(
            session, ids["demo_owner_id"], "dono.demo@deepfarms.com.br", ids["demo_tenant_id"], TenantRoles.OWNER
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        inv_a = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {owner_tok}"},
            json={"email": "visita.a@agro.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
        )
        inv_b = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {owner_tok}"},
            json={"email": "visita.b@agro.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
        )
        tok_a = (await client.post(
            "/api/v1/onboarding/convites/registrar",
            json={"token": inv_a.json()["token"], "senha": "MinhaSenha123!", "nome_completo": "Visitante A"},
        )).json()["access_token"]
        tok_b = (await client.post(
            "/api/v1/onboarding/convites/registrar",
            json={"token": inv_b.json()["token"], "senha": "MinhaSenha123!", "nome_completo": "Visitante B"},
        )).json()["access_token"]

        for path in (
            "/api/v1/team/users",
            "/api/v1/audit-log",
            "/api/v1/sessions/team",
            "/api/v1/cadastros/pessoas/123/pii",
            "/api/v1/ia/assistente",
            "/api/v1/campo/sync",
        ):
            r = await client.get(path, headers={"Authorization": f"Bearer {tok_a}"})
            assert r.status_code == 403, f"Esperado 403 em {path}, obteve {r.status_code}"
            assert r.headers.get("X-Error-Code") == "READ_ONLY_RESTRICTED_RESOURCE"

        # Visitante A abre chamado; Visitante B não enxerga nem consegue interagir
        ticket_a = await client.post(
            "/api/v1/support/tickets",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"assunto": "Dúvida comercial privada", "categoria": "COMERCIAL", "mensagem_inicial": "Olá"},
        )
        assert ticket_a.status_code == 200
        ticket_a_id = ticket_a.json()["id"]

        list_b = await client.get("/api/v1/support/tickets", headers={"Authorization": f"Bearer {tok_b}"})
        assert list_b.status_code == 200
        assert list_b.json() == []

        detail_b = await client.get(f"/api/v1/support/tickets/{ticket_a_id}", headers={"Authorization": f"Bearer {tok_b}"})
        assert detail_b.status_code == 404

        reply_b = await client.post(
            f"/api/v1/support/tickets/{ticket_a_id}/messages",
            headers={"Authorization": f"Bearer {tok_b}"},
            json={"conteudo": "Tentativa indevida"},
        )
        assert reply_b.status_code == 404

        # Verifica sinalização de isolamento no resolvedor WebSocket
        user_id_b, is_admin_b, _, is_isolated_b = await support_ws_module._resolve_user_from_token(tok_b)
        assert is_admin_b is False
        assert is_isolated_b is True
        assert user_id_b is not None


@pytest.mark.asyncio
async def test_demo_concurrent_session_cap_and_owner_expired_exemptions(demo_app):
    """Limita visitantes simultâneos com 429 sem contar dono interno ou visitante expirado."""
    app, session_factory = demo_app
    async with session_factory() as session:
        ids = await _seed_demo_environment(session)
        admin_tok = _make_backoffice_token(
            session, ids["admin_id"], "admin@deepfarms.com.br", "super_admin", is_superuser=True
        )
        owner_tok = _make_tenant_token(
            session, ids["demo_owner_id"], "dono.demo@deepfarms.com.br", ids["demo_tenant_id"], TenantRoles.OWNER
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Backoffice ajusta teto simultâneo para 2 visitantes no Produtor DeepFarms
        cfg = await client.patch(
            f"/api/v1/backoffice/tenants/{ids['demo_tenant_id']}/demo-config",
            headers={"Authorization": f"Bearer {admin_tok}"},
            json={"is_demo": True, "demo_max_sessoes_simultaneas": 2},
        )
        assert cfg.status_code == 200
        assert cfg.json()["demo_max_sessoes_simultaneas"] == 2

        for idx in range(1, 5):
            inv = await client.post(
                "/api/v1/team/invite",
                headers={"Authorization": f"Bearer {owner_tok}"},
                json={"email": f"v{idx}@demo.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
            )
            await client.post(
                "/api/v1/onboarding/convites/registrar",
                json={"token": inv.json()["token"], "senha": "MinhaSenha123!", "nome_completo": f"V{idx}"},
            )

        # Marca v4 como expirado para confirmar que não consome slot
        async with session_factory() as session:
            u4 = (await session.execute(select(Usuario).where(Usuario.email == "v4@demo.com.br"))).scalar_one()
            tu4 = (await session.execute(select(TenantUsuario).where(TenantUsuario.usuario_id == u4.id))).scalar_one()
            tu4.data_validade_acesso = date.today() - timedelta(days=2)
            await session.commit()

        # Limpa sessões eventualmente geradas no registro para testar contagem exata do /auth/login
        async with session_factory() as session:
            for s in (await session.execute(select(SessaoAtiva))).scalars().all():
                await session.delete(s)
            await session.commit()

        # Dono interno consegue logar sem consumir vaga de visitante
        l_owner = await client.post(
            "/api/v1/auth/login",
            json={"email": "dono.demo@deepfarms.com.br", "senha": "SenhaForte123!"},
        )
        assert l_owner.status_code == 200

        # Visitantes 1 e 2 ocupam os 2 slots
        assert (await client.post("/api/v1/auth/login", json={"email": "v1@demo.com.br", "senha": "MinhaSenha123!"})).status_code == 200
        assert (await client.post("/api/v1/auth/login", json={"email": "v2@demo.com.br", "senha": "MinhaSenha123!"})).status_code == 200

        # Visitante 3 recebe 429 DEMO_CONCURRENCY_LIMIT
        l3 = await client.post("/api/v1/auth/login", json={"email": "v3@demo.com.br", "senha": "MinhaSenha123!"})
        assert l3.status_code == 429
        assert l3.headers.get("X-Error-Code") == "DEMO_CONCURRENCY_LIMIT"
        assert "demonstra" in l3.json()["detail"].lower()

        # Visitante 4 (expirado) ainda consegue logar para abrir chamado de prorrogação
        l4 = await client.post("/api/v1/auth/login", json={"email": "v4@demo.com.br", "senha": "MinhaSenha123!"})
        assert l4.status_code == 200


@pytest.mark.asyncio
async def test_demo_expiration_and_unlimited_audited_commercial_extension(demo_app):
    """Expiração bloqueia módulos, abre suporte, e Comercial prorroga ilimitadamente com auditoria."""
    app, session_factory = demo_app
    async with session_factory() as session:
        ids = await _seed_demo_environment(session)
        owner_tok = _make_tenant_token(
            session, ids["demo_owner_id"], "dono.demo@deepfarms.com.br", ids["demo_tenant_id"], TenantRoles.OWNER
        )
        comercial_tok = _make_backoffice_token(
            session, ids["comercial_id"], "comercial@deepfarms.com.br", "comercial"
        )
        suporte_tok = _make_backoffice_token(
            session, ids["suporte_id"], "suporte@deepfarms.com.br", "suporte"
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        inv = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {owner_tok}"},
            json={"email": "expirado@demo.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
        )
        await client.post(
            "/api/v1/onboarding/convites/registrar",
            json={"token": inv.json()["token"], "senha": "MinhaSenha123!", "nome_completo": "Visitante Expirado"},
        )

        # Força vencimento ontem
        async with session_factory() as session:
            u_exp = (await session.execute(select(Usuario).where(Usuario.email == "expirado@demo.com.br"))).scalar_one()
            tu_exp = (await session.execute(select(TenantUsuario).where(TenantUsuario.usuario_id == u_exp.id))).scalar_one()
            tu_exp.data_validade_acesso = date.today() - timedelta(days=1)
            await session.commit()

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "expirado@demo.com.br", "senha": "MinhaSenha123!"},
        )
        assert login_resp.status_code == 200
        exp_token = login_resp.json()["access_token"]

        # /auth/me informa estado expirado
        me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {exp_token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["tenants"][0]["demo_expired"] is True

        # Módulo de negócio bloqueado com 403 DEMO_ACCESS_EXPIRED
        blocked_mod = await client.get("/api/v1/demo-probe/read", headers={"Authorization": f"Bearer {exp_token}"})
        assert blocked_mod.status_code == 403
        assert blocked_mod.headers.get("X-Error-Code") == "DEMO_ACCESS_EXPIRED"

        # Suporte permanece aberto e impede duplicidade de solicitação aberta
        ticket_1 = await client.post(
            "/api/v1/support/tickets",
            headers={"Authorization": f"Bearer {exp_token}"},
            json={
                "assunto": "Solicito prorrogação de 15 dias",
                "categoria": DEMO_EXTENSION_TICKET_CATEGORY,
                "prioridade": "ALTA",
                "mensagem_inicial": "Quero continuar avaliando.",
            },
        )
        assert ticket_1.status_code == 200
        ticket_1_id = ticket_1.json()["id"]

        dup_ticket = await client.post(
            "/api/v1/support/tickets",
            headers={"Authorization": f"Bearer {exp_token}"},
            json={
                "assunto": "Segunda solicitação duplicada",
                "categoria": DEMO_EXTENSION_TICKET_CATEGORY,
                "mensagem_inicial": "Duplicada",
            },
        )
        assert dup_ticket.status_code == 409

        # Analista de suporte comum NÃO pode aprovar prorrogação
        forbid_suporte = await client.post(
            f"/api/v1/backoffice/tickets/{ticket_1_id}/aprovar-prorrogacao-demo",
            headers={"Authorization": f"Bearer {suporte_tok}"},
            json={"dias": 15},
        )
        assert forbid_suporte.status_code == 403

        # Equipe Comercial lista chamados e aprova 1ª prorrogação
        bo_list = await client.get("/api/v1/backoffice/tickets", headers={"Authorization": f"Bearer {comercial_tok}"})
        assert bo_list.status_code == 200
        listed = next(item for item in bo_list.json() if item["id"] == ticket_1_id)
        assert listed["is_demo_tenant"] is True
        assert listed["data_validade_acesso"] is not None

        approve_1 = await client.post(
            f"/api/v1/backoffice/tickets/{ticket_1_id}/aprovar-prorrogacao-demo",
            headers={"Authorization": f"Bearer {comercial_tok}"},
            json={"dias": 15, "observacao": "Lead engajado"},
        )
        assert approve_1.status_code == 200
        assert approve_1.json()["demo_prorrogacoes_count"] == 1
        first_new_expiry = date.fromisoformat(approve_1.json()["data_validade_acesso"])
        assert first_new_expiry == date.today() + timedelta(days=15)

        # Novo login imediato libera módulos
        relogin = await client.post(
            "/api/v1/auth/login",
            json={"email": "expirado@demo.com.br", "senha": "MinhaSenha123!"},
        )
        fresh_token = relogin.json()["access_token"]
        unblocked = await client.get("/api/v1/demo-probe/read", headers={"Authorization": f"Bearer {fresh_token}"})
        assert unblocked.status_code == 200

        # 2ª prorrogação livre após novo chamado (sem teto de quantidade, sempre auditada)
        ticket_2 = await client.post(
            "/api/v1/support/tickets",
            headers={"Authorization": f"Bearer {fresh_token}"},
            json={
                "assunto": "Nova prorrogação de 15 dias",
                "categoria": DEMO_EXTENSION_TICKET_CATEGORY,
                "mensagem_inicial": "Segunda renovação.",
            },
        )
        assert ticket_2.status_code == 200
        approve_2 = await client.post(
            f"/api/v1/backoffice/tickets/{ticket_2.json()['id']}/aprovar-prorrogacao-demo",
            headers={"Authorization": f"Bearer {comercial_tok}"},
            json={"dias": 15},
        )
        assert approve_2.status_code == 200
        assert approve_2.json()["demo_prorrogacoes_count"] == 2
        assert date.fromisoformat(approve_2.json()["data_validade_acesso"]) == first_new_expiry + timedelta(days=15)

    async with session_factory() as session:
        audit_logs = (
            await session.execute(
                select(AdminAuditLog).where(AdminAuditLog.acao == "DEMO_ACCESS_EXTENDED")
            )
        ).scalars().all()
        assert len(audit_logs) == 2

        lead = (
            await session.execute(select(LeadCRM).where(LeadCRM.email == "expirado@demo.com.br"))
        ).scalar_one()
        atividades = (
            await session.execute(select(AtividadeCRM).where(AtividadeCRM.lead_id == lead.id))
        ).scalars().all()
        assert any("Prorrogação" in a.descricao or "prorroga" in a.descricao.lower() for a in atividades)


@pytest.mark.asyncio
async def test_demo_saas_config_persistence_and_dynamic_behavior(demo_app):
    """Persistência da chave 'demonstracao' em configuracoes_saas dirige prazo, CRM, 429 e prorrogação."""
    app, session_factory = demo_app
    async with session_factory() as session:
        ids = await _seed_demo_environment(session)
        admin_tok = _make_backoffice_token(
            session, ids["admin_id"], "admin@deepfarms.com.br", "super_admin", is_superuser=True
        )
        comercial_tok = _make_backoffice_token(
            session, ids["comercial_id"], "comercial@deepfarms.com.br", "comercial"
        )
        owner_tok = _make_tenant_token(
            session, ids["demo_owner_id"], "dono.demo@deepfarms.com.br", ids["demo_tenant_id"], TenantRoles.OWNER
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Payload inválido deve retornar 422
        invalid_resp = await client.put(
            "/api/v1/config/saas/demonstracao",
            headers={"Authorization": f"Bearer {admin_tok}"},
            json={"valor": {"max_sessoes_simultaneas": 0}},
        )
        assert invalid_resp.status_code == 422

        # Persistência de parâmetros personalizados em configuracoes_saas
        custom_msg = "Capacidade de demonstração atingida no momento. Tente em instantes."
        save_resp = await client.put(
            "/api/v1/config/saas/demonstracao",
            headers={"Authorization": f"Bearer {admin_tok}"},
            json={
                "valor": {
                    "tenant_id": str(ids["demo_tenant_id"]),
                    "max_sessoes_simultaneas": 1,
                    "duracao_inicial_dias": 21,
                    "dias_prorrogacao_padrao": 10,
                    "timeout_inatividade_minutos": 15,
                    "estagio_crm_nome": "Demo Qualificada",
                    "mensagem_limite_simultaneo": custom_msg,
                    "permitir_solicitacao_prorrogacao": True,
                }
            },
        )
        assert save_resp.status_code == 200
        assert save_resp.json()["chave"] == "demonstracao"

        # Novo visitante recebe prazo de 21 dias e lead no estágio "Demo Qualificada"
        inv1 = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {owner_tok}"},
            json={"email": "cfg1@demo.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
        )
        reg1 = await client.post(
            "/api/v1/onboarding/convites/registrar",
            json={"token": inv1.json()["token"], "senha": "MinhaSenha123!", "nome_completo": "Cfg 1"},
        )
        assert reg1.status_code == 200

        inv2 = await client.post(
            "/api/v1/team/invite",
            headers={"Authorization": f"Bearer {owner_tok}"},
            json={"email": "cfg2@demo.com.br", "perfil_id": str(ids["perfil_gestor_id"])},
        )
        # 2º visitante esbarra no limite 1 e recebe mensagem personalizada
        reg2 = await client.post(
            "/api/v1/onboarding/convites/registrar",
            json={"token": inv2.json()["token"], "senha": "MinhaSenha123!", "nome_completo": "Cfg 2"},
        )
        assert reg2.status_code == 429
        assert reg2.headers.get("X-Error-Code") == "DEMO_CONCURRENCY_LIMIT"
        assert reg2.json()["detail"] == custom_msg

        # Chamado de prorrogação sem 'dias' explícito aplica dias_prorrogacao_padrao=10
        tok1 = reg1.json()["access_token"]
        tkt = await client.post(
            "/api/v1/support/tickets",
            headers={"Authorization": f"Bearer {tok1}"},
            json={
                "assunto": "Solicitar prorrogação dinâmica",
                "categoria": DEMO_EXTENSION_TICKET_CATEGORY,
                "mensagem_inicial": "Teste de configuração persistida.",
            },
        )
        assert tkt.status_code == 200

        approve = await client.post(
            f"/api/v1/backoffice/tickets/{tkt.json()['id']}/aprovar-prorrogacao-demo",
            headers={"Authorization": f"Bearer {comercial_tok}"},
            json={},
        )
        assert approve.status_code == 200
        assert date.fromisoformat(approve.json()["data_validade_acesso"]) == date.today() + timedelta(days=31)

        # Desabilitar solicitação de prorrogação bloqueia novos pedidos com 403
        disable_resp = await client.put(
            "/api/v1/config/saas/demonstracao",
            headers={"Authorization": f"Bearer {admin_tok}"},
            json={
                "valor": {
                    "tenant_id": str(ids["demo_tenant_id"]),
                    "max_sessoes_simultaneas": 1,
                    "duracao_inicial_dias": 21,
                    "dias_prorrogacao_padrao": 10,
                    "timeout_inatividade_minutos": 15,
                    "estagio_crm_nome": "Demo Qualificada",
                    "mensagem_limite_simultaneo": custom_msg,
                    "permitir_solicitacao_prorrogacao": False,
                }
            },
        )
        assert disable_resp.status_code == 200

        blocked_req = await client.post(
            "/api/v1/support/tickets",
            headers={"Authorization": f"Bearer {tok1}"},
            json={
                "assunto": "Bloqueada pela config",
                "categoria": DEMO_EXTENSION_TICKET_CATEGORY,
                "mensagem_inicial": "Tentativa bloqueada.",
            },
        )
        assert blocked_req.status_code == 403

    async with session_factory() as session:
        demo_tenant = await session.get(Tenant, ids["demo_tenant_id"])
        assert demo_tenant is not None
        assert demo_tenant.is_demo is True
        assert demo_tenant.demo_max_sessoes_simultaneas == 1

        cfg_row = (
            await session.execute(select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == "demonstracao"))
        ).scalar_one()
        assert cfg_row.valor["duracao_inicial_dias"] == 21

        stage_custom = (
            await session.execute(select(PipelineEstagio).where(PipelineEstagio.nome == "Demo Qualificada"))
        ).scalar_one_or_none()
        assert stage_custom is not None

        u1 = (await session.execute(select(Usuario).where(Usuario.email == "cfg1@demo.com.br"))).scalar_one()
        tu1 = (await session.execute(select(TenantUsuario).where(TenantUsuario.usuario_id == u1.id))).scalar_one()
        assert tu1.data_validade_acesso == date.today() + timedelta(days=31)

        cfg_audits = (
            await session.execute(select(AdminAuditLog).where(AdminAuditLog.acao == "saas.config.update"))
        ).scalars().all()
        assert len(cfg_audits) >= 2
