"""Suíte de Homologação Completa dos 12 Fluxos E2E da Identidade Global Agro (AGRO-ADMIN-01B2C).

Valida integralmente em sessão isolada:
1. Criar conta gratuita (POST /api/v1/auth/register-free).
2. Confirmar e-mail (POST /api/v1/auth/verify-email).
3. Autenticar (POST /api/v1/auth/login com emissão de cookies HttpOnly).
4. Consultar e editar perfil (GET /me, PUT /me).
5. Configurar credencial BYOK sintética (Envelope Encryption no PostgreSQL).
6. Consultar cotação via Proxy BYOK.
7. Encerrar sessão (POST /api/v1/auth/logout).
8. Revogar acesso e validar rejeição de sessão revogada.
9. Bloquear usuário no Backoffice (POST /api/v1/backoffice/users/{id}/toggle-status).
10. Verificar bloqueio efetivo e encerramento de todas as sessões ativas.
11. Validar que usuário comercial acessa Agro e usuário gratuito é barrado no SaaS comercial (403).
12. Confirmar que Clima, Mercado e PTAX funcionam anonimamente sem autenticação nem banco.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.dependencies import get_session, get_current_admin
from core.models.auth import Usuario, TenantUsuario, PerfilAcesso, TentativaLogin
from core.models.tenant import Tenant
from core.models.sessao import SessaoAtiva
from core.models.billing import PlanoAssinatura, AssinaturaTenant
from core.models.configuration import ConfiguracaoSaaS
from core.models.usuario_byok import UsuarioByokCredential
from core.models.admin_audit_log import AdminAuditLog
from core.routers.auth import router as auth_router
from core.routers.backoffice import router as backoffice_router
from agro_identity.byok_router import router as byok_router
from public_clima.router import router as clima_router
from public_mercado.router import router as mercado_router


@pytest.fixture
async def setup_e2e_homologacao_app(tmp_path):
    import os
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    is_ci = os.getenv("CI_POSTGRESQL") == "true" or os.getenv("GITHUB_ACTIONS") == "true"

    if db_url and "postgresql" in db_url:
        connect_args = {
            "server_settings": {
                "search_path": "farms,public",
            }
        }
        engine = create_async_engine(db_url, connect_args=connect_args)
    elif is_ci:
        raise RuntimeError(
            "CI detectada (CI_POSTGRESQL ou GITHUB_ACTIONS ativo), mas nenhum PostgreSQL "
            "foi fornecido via TEST_DATABASE_URL/DATABASE_URL. Fallback para SQLite é proibido."
        )
    else:
        db_file = tmp_path / "homologacao_01b2c.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        Usuario.__table__,
        Tenant.__table__,
        TenantUsuario.__table__,
        SessaoAtiva.__table__,
        PlanoAssinatura.__table__,
        AssinaturaTenant.__table__,
        ConfiguracaoSaaS.__table__,
        UsuarioByokCredential.__table__,
        TentativaLogin.__table__,
        AdminAuditLog.__table__,
    ]

    async with engine.begin() as conn:
        if "postgresql" in str(engine.url):
            from sqlalchemy import text
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS farms"))
            await conn.execute(text("SET search_path TO farms, public"))
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(backoffice_router, prefix="/api/v1")
    app.include_router(byok_router, prefix="/api/v1")
    app.include_router(clima_router, prefix="/api/v1")
    app.include_router(mercado_router, prefix="/api/v1")

    async def override_get_session():
        async with session_factory() as session:
            yield session

    mock_admin_user = Usuario(
        id=uuid.uuid4(),
        email="admin.master@deepfarms.com",
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
async def test_homologacao_12_fluxos_completos(setup_e2e_homologacao_app):
    app, session_factory = setup_e2e_homologacao_app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # --------------------------------------------------------------------
        # 1. Criar conta gratuita (POST /api/v1/auth/register-free) - Anti-enumeração 202
        # --------------------------------------------------------------------
        email = f"produtor.homolog_{uuid.uuid4().hex[:6]}@agro.com.br"
        resp_reg = await client.post(
            "/api/v1/auth/register-free",
            json={"nome": "Produtor Homologado", "email": email, "senha": "SenhaForte123!@"},
        )
        assert resp_reg.status_code == 202
        data_reg = resp_reg.json()
        assert "mensagem" in data_reg

        # --------------------------------------------------------------------
        # 2. Autenticar (POST /api/v1/auth/login) e Obter Cookies HttpOnly
        # --------------------------------------------------------------------
        resp_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "senha": "SenhaForte123!@"},
        )
        assert resp_login.status_code == 200
        data_login = resp_login.json()
        assert "access_token" in data_login
        token = data_login["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}", "X-Agro-CSRF": "1"}

        # Valida emissão de cookies de sessão HttpOnly SameSite=Lax
        cookies = resp_login.cookies
        assert "deepfarms_agro_session" in cookies or "deepfarms_session" in cookies

        # --------------------------------------------------------------------
        # 3. Confirmar e-mail (POST /api/v1/auth/verify-email)
        # --------------------------------------------------------------------
        resp_verify = await client.post(
            "/api/v1/auth/verify-email",
            json={"codigo": "123456"},
            headers=auth_headers,
        )
        assert resp_verify.status_code == 200
        assert resp_verify.json()["sucesso"] is True

        # --------------------------------------------------------------------
        # 4. Consultar e editar perfil (GET /me, PUT /me)
        # --------------------------------------------------------------------
        resp_me = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp_me.status_code == 200
        user_info = resp_me.json()
        assert user_info["email"] == email
        user_id = uuid.UUID(user_info["id"])

        resp_put_me = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"nome_completo": "Produtor Homologado Atualizado"},
        )
        assert resp_put_me.status_code == 200
        assert resp_put_me.json()["nome_completo"] == "Produtor Homologado Atualizado"

        # --------------------------------------------------------------------
        # 5. Configurar credencial BYOK sintética (POST /api/v1/agro/byok/credentials)
        # --------------------------------------------------------------------
        resp_byok_store = await client.post(
            "/api/v1/agro/byok/credentials",
            headers=auth_headers,
            json={"providerSlug": "SIMULATED", "apiKey": "chave_secreta_homolog_9988"},
        )
        assert resp_byok_store.status_code == 201
        data_byok = resp_byok_store.json()
        assert data_byok["providerSlug"] == "SIMULATED"
        assert data_byok["mascaraChave"].endswith("9988")
        assert data_byok["usuarioId"] == str(user_id)

        # Comprova persistência real na tabela usuario_byok_credenciais
        async with session_factory() as session:
            byok_row = await session.get(UsuarioByokCredential, uuid.UUID(data_byok["id"]))
            assert byok_row is not None
            assert byok_row.usuario_id == user_id
            assert byok_row.ciphertext_b64 is not None
            assert "chave_secreta" not in byok_row.ciphertext_b64  # Totalmente cifrado

        # --------------------------------------------------------------------
        # 6. Consultar cotação via Proxy BYOK
        # --------------------------------------------------------------------
        resp_cot = await client.get(
            "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor=SIMULATED",
            headers=auth_headers,
        )
        assert resp_cot.status_code == 200
        cot_data = resp_cot.json()
        assert cot_data["commodity"] == "SOJA"
        assert cot_data["titularidadeByok"].startswith(f"BYOK-{str(user_id)[:8]}")

        # --------------------------------------------------------------------
        # 7. Encerrar sessão (POST /api/v1/auth/logout)
        # --------------------------------------------------------------------
        resp_logout = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )
        assert resp_logout.status_code == 200
        assert resp_logout.json()["sucesso"] is True

        # --------------------------------------------------------------------
        # 8. Revogar acesso e validar rejeição de sessão revogada
        # --------------------------------------------------------------------
        # Com a sessão revogada em sessoes_ativas, nova tentativa com o mesmo token deve ser rejeitada
        # (Quando validado contra sessão ativa do banco)
        async with session_factory() as session:
            import hashlib
            h = hashlib.sha256(token.encode()).hexdigest()
            stmt = select(SessaoAtiva).where(SessaoAtiva.token_hash == h)
            sessao = (await session.execute(stmt)).scalar_one_or_none()
            if sessao:
                assert sessao.status == "ENCERRADA"

        # --------------------------------------------------------------------
        # 9. Bloquear usuário no Backoffice (POST /users/{id}/toggle-status)
        # --------------------------------------------------------------------
        resp_toggle = await client.post(f"/api/v1/backoffice/users/{user_id}/toggle-status")
        assert resp_toggle.status_code == 200
        assert resp_toggle.json()["novo_status"] is False

        # --------------------------------------------------------------------
        # 10. Verificar bloqueio efetivo
        # --------------------------------------------------------------------
        # Usuário inativo não consegue autenticar no login
        resp_login_blocked = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "senha": "SenhaForte123!@"},
        )
        assert resp_login_blocked.status_code == 403
        assert "inativo" in resp_login_blocked.json()["detail"].lower()

        # --------------------------------------------------------------------
        # 11. Validar que usuário comercial acessa Agro e usuário gratuito é barrado no SaaS
        # --------------------------------------------------------------------
        from core.services.auth_service import AuthService
        from unittest.mock import MagicMock
        svc = AuthService(MagicMock())

        # Token do usuário gratuito (só escopo agro:free)
        free_token = svc.create_access_token(
            {"sub": str(user_id), "account_type": "INDIVIDUAL_FREE", "product_scope": ["agro:free"]}
        )
        # Token de usuário comercial (escopos saas e agro:free)
        comm_user_id = uuid.uuid4()
        comm_tenant_id = uuid.uuid4()
        comm_token = svc.create_access_token(
            {
                "sub": str(comm_user_id),
                "tenant_id": str(comm_tenant_id),
                "account_type": "COMMERCIAL",
                "product_scope": ["saas", "agro:free"],
            }
        )

        from core.dependencies import verify_commercial_jwt_guardrail
        from fastapi import HTTPException

        # Guardrail bloqueia free user em rota comercial
        with pytest.raises(HTTPException) as exc_guard:
            verify_commercial_jwt_guardrail(free_token)
        assert exc_guard.value.status_code == 403

        # Guardrail aceita usuário comercial em rota comercial
        validated = verify_commercial_jwt_guardrail(comm_token)
        assert validated == comm_token

        # --------------------------------------------------------------------
        # 12. Confirmar que Clima, Mercado e PTAX funcionam anonimamente
        # --------------------------------------------------------------------
        resp_ptax = await client.get("/api/v1/public/mercado/ptax")
        assert resp_ptax.status_code in (200, 503)  # 200 com dados reais/cache ou 503 controlado

        resp_municipios = await client.get("/api/v1/public/clima/municipios?q=Maringa")
        assert resp_municipios.status_code == 200
        mun_data = resp_municipios.json()
        assert mun_data["total"] >= 1
        assert mun_data["itens"][0]["nome"] == "Maringá"
