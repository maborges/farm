"""Suíte de testes de integração, segurança e conformidade para AGRO-ADMIN-01H1.

Valida exaustivamente:
1. Endpoint de Heartbeat (/api/v1/auth/heartbeat) com cookies HttpOnly, CSRF, rate-limiting e bloqueio de sessões expiradas/inativas.
2. Reserva atômica de cotas de provedores climáticos em ClimaCache e rollback em falhas upstream.
3. Isolamento criptográfico estrito de PLATFORM_CREDENTIALS_MASTER_KEY em staging/produção e recifragem para KEK v2.
4. Matriz de Homologação estrita baseada em evidências verificáveis (3/11 = 27.3%).
5. Validador de isolamento de infraestrutura de staging (scripts/staging/validate_isolation.py).
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import settings
from core.database import Base
from core.dependencies import get_current_admin, get_session
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_user import AdminUser
from core.models.auth import TenantUsuario, Usuario
from core.models.configuration import ConfiguracaoSaaS
from core.models.sessao import SessaoAtiva
from core.models.tenant import Tenant
from core.models.usuario_byok import UsuarioByokCredential
from core.routers.auth import _HEARTBEAT_CACHE, router as auth_router
from core.routers.backoffice_agro_dashboard import PERM_VIEW, router as agro_dashboard_router
from core.schemas.agro_config_schemas import KEY_CREDENTIALS_CLIMA
from core.services.auth_service import AuthService, hash_password
from core.services.platform_weather_credentials import (
    PlatformWeatherCredentialsService,
    _derive_platform_kek,
)
from public_clima.adapters import is_provider_authorized_for_public
from public_clima.cache import ClimaCache
from scripts.staging.validate_isolation import validate_staging_config

COOKIE_NAME = "deepfarms_agro_session"


# ==============================================================================
# Fixtures e Configuração de Banco Isolado
# ==============================================================================

@pytest.fixture
async def setup_01h1_env(tmp_path):
    """Configura banco SQLite assíncrono isolado para os testes de sessão e configuração."""
    db_file = tmp_path / "test_agro_01h1.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        ConfiguracaoSaaS.__table__,
        AdminAuditLog.__table__,
        AdminUser.__table__,
        Usuario.__table__,
        Tenant.__table__,
        TenantUsuario.__table__,
        SessaoAtiva.__table__,
        UsuarioByokCredential.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=tables)
        await conn.run_sync(Base.metadata.create_all, tables=tables)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


@pytest.fixture
def test_app(setup_01h1_env):
    """Cria instância FastAPI com routers de autenticação e dashboard."""
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(agro_dashboard_router, prefix="/api/v1")

    async def override_get_session():
        async with setup_01h1_env() as session:
            yield session

    async def override_get_current_admin():
        return {
            "sub": str(uuid.uuid4()),
            "email": "auditor_staging@deepfarms.com",
            "is_superuser": True,
            "permissions": ["admin:read", "admin:write", "agro:admin", "agro:config:read", *PERM_VIEW],
        }

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_admin] = override_get_current_admin
    return app


# ==============================================================================
# 1. TESTES DO HEARTBEAT DA PWA AGRO
# ==============================================================================

@pytest.mark.asyncio
async def test_heartbeat_com_cookie_httponly_sucesso(test_app, setup_01h1_env):
    """Heartbeat autenticado com cookie HttpOnly e CSRF atualiza ultimo_heartbeat."""
    _HEARTBEAT_CACHE.clear()
    user_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    auth_srv = AuthService(None)
    token = auth_srv.create_access_token({"sub": str(user_id), "email": "produtor_pwa@agro.com"})
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    async with setup_01h1_env() as session:
        user = Usuario(
            id=user_id,
            email="produtor_pwa@agro.com",
            username="produtor_pwa",
            nome_completo="Produtor PWA Agro",
            senha_hash=hash_password("SenhaForte@123"),
            ativo=True,
            is_superuser=False,
        )
        session.add(user)
        sessao = SessaoAtiva(
            usuario_id=user_id,
            token_hash=token_hash,
            ip_address="127.0.0.1",
            user_agent="PWA-Agro-Test/1.0",
            inicio=now_utc - timedelta(minutes=10),
            ultimo_heartbeat=now_utc - timedelta(minutes=5),
            expira_em=now_utc + timedelta(hours=2),
            status="ATIVA",
        )
        session.add(sessao)
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        cookies={COOKIE_NAME: token},
    ) as client:
        response = await client.post(
            "/api/v1/auth/heartbeat",
            headers={"X-Agro-CSRF": "1"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["throttled"] is False

    # Confirma persistência de atualização no banco
    async with setup_01h1_env() as session:
        stmt = select(SessaoAtiva).where(SessaoAtiva.token_hash == token_hash)
        res = await session.execute(stmt)
        updated_sessao = res.scalar_one()
        assert updated_sessao.ultimo_heartbeat is not None
        hb = updated_sessao.ultimo_heartbeat
        if hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        assert hb > (now_utc - timedelta(minutes=1))


@pytest.mark.asyncio
async def test_heartbeat_rate_limiting_memoria(test_app, setup_01h1_env):
    """Heartbeat repetido dentro da janela de 60s é respondido sem gravação desnecessária."""
    _HEARTBEAT_CACHE.clear()
    user_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    auth_srv = AuthService(None)
    token = auth_srv.create_access_token({"sub": str(user_id), "email": "produtor_throttle@agro.com"})
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    async with setup_01h1_env() as session:
        user = Usuario(
            id=user_id,
            email="produtor_throttle@agro.com",
            username="produtor_throttle",
            nome_completo="Produtor Throttle",
            senha_hash=hash_password("SenhaForte@123"),
            ativo=True,
            is_superuser=False,
        )
        session.add(user)
        sessao = SessaoAtiva(
            usuario_id=user_id,
            token_hash=token_hash,
            ip_address="127.0.0.1",
            user_agent="PWA-Agro-Test/1.0",
            inicio=now_utc,
            ultimo_heartbeat=now_utc,
            expira_em=now_utc + timedelta(hours=2),
            status="ATIVA",
        )
        session.add(sessao)
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        cookies={COOKIE_NAME: token},
    ) as client:
        # Primeira chamada: atualiza
        r1 = await client.post(
            "/api/v1/auth/heartbeat",
            headers={"X-Agro-CSRF": "1"},
        )
        assert r1.status_code == 200
        assert r1.json()["throttled"] is False

        # Segunda chamada imediata (mesmo segundo): throttled
        r2 = await client.post(
            "/api/v1/auth/heartbeat",
            headers={"X-Agro-CSRF": "1"},
        )
        assert r2.status_code == 200
        assert r2.json()["throttled"] is True


@pytest.mark.asyncio
async def test_heartbeat_rejeita_csrf_invalido(test_app, setup_01h1_env):
    """Heartbeat via cookie HttpOnly com origem não autorizada ou cross-site sem CSRF é rejeitado."""
    _HEARTBEAT_CACHE.clear()
    auth_srv = AuthService(None)
    token = auth_srv.create_access_token({"sub": str(uuid.uuid4()), "email": "pwa_csrf@agro.com"})

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        cookies={COOKIE_NAME: token},
    ) as client:
        response = await client.post(
            "/api/v1/auth/heartbeat",
            headers={"sec-fetch-site": "cross-site"},
        )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_heartbeat_rejeita_sessao_expirada(test_app, setup_01h1_env):
    """Heartbeat com sessão inexistente ou encerrada retorna HTTP 401."""
    _HEARTBEAT_CACHE.clear()
    user_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    auth_srv = AuthService(None)
    token = auth_srv.create_access_token({"sub": str(user_id), "email": "produtor_exp@agro.com"})
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    async with setup_01h1_env() as session:
        user = Usuario(
            id=user_id,
            email="produtor_exp@agro.com",
            username="produtor_exp",
            nome_completo="Produtor Expirado",
            senha_hash=hash_password("SenhaForte@123"),
            ativo=True,
            is_superuser=False,
        )
        session.add(user)
        sessao = SessaoAtiva(
            usuario_id=user_id,
            token_hash=token_hash,
            ip_address="127.0.0.1",
            user_agent="PWA-Agro-Test/1.0",
            inicio=now_utc - timedelta(hours=5),
            ultimo_heartbeat=now_utc - timedelta(hours=3),
            expira_em=now_utc - timedelta(minutes=10),
            status="ENCERRADA",
        )
        session.add(sessao)
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        cookies={COOKIE_NAME: token},
    ) as client:
        response = await client.post(
            "/api/v1/auth/heartbeat",
            headers={"X-Agro-CSRF": "1"},
        )
    assert response.status_code == 401
    assert "sessão" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_heartbeat_rejeita_usuario_bloqueado(test_app, setup_01h1_env):
    """Heartbeat de usuário inativo/bloqueado retorna HTTP 403."""
    _HEARTBEAT_CACHE.clear()
    user_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    auth_srv = AuthService(None)
    token = auth_srv.create_access_token({"sub": str(user_id), "email": "produtor_bloqueado@agro.com"})
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    async with setup_01h1_env() as session:
        user = Usuario(
            id=user_id,
            email="produtor_bloqueado@agro.com",
            username="produtor_bloqueado",
            nome_completo="Produtor Bloqueado",
            senha_hash=hash_password("SenhaForte@123"),
            ativo=False,  # Bloqueado/inativo
            is_superuser=False,
        )
        session.add(user)
        sessao = SessaoAtiva(
            usuario_id=user_id,
            token_hash=token_hash,
            ip_address="127.0.0.1",
            user_agent="PWA-Agro-Test/1.0",
            inicio=now_utc - timedelta(minutes=5),
            ultimo_heartbeat=now_utc - timedelta(minutes=2),
            expira_em=now_utc + timedelta(hours=1),
            status="ATIVA",
        )
        session.add(sessao)
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        cookies={COOKIE_NAME: token},
    ) as client:
        response = await client.post(
            "/api/v1/auth/heartbeat",
            headers={"X-Agro-CSRF": "1"},
        )
    assert response.status_code == 403
    assert "inativo" in response.json()["detail"].lower() or "bloqueado" in response.json()["detail"].lower()


# ==============================================================================
# 2. TESTES DE RESERVA ATÔMICA DE COTAS CLIMÁTICAS
# ==============================================================================

@pytest.mark.asyncio
async def test_clima_cache_atomic_quota_reservation_and_rollback():
    """Testa reserva atômica via Lua e reversão (rollback) em ClimaCache."""
    cache = ClimaCache(redis_url="redis://localhost:6379/0")

    # Simula cliente Redis mock
    mock_redis = AsyncMock()
    mock_redis.eval = AsyncMock(return_value=[1, 42])
    mock_redis.decr = AsyncMock(return_value=41)
    cache.redis = mock_redis

    # 1. Reserva atômica aprovada
    reserved, count = await cache.reserve_monthly_quota("WEATHERAPI", limit=100000, shared=True)
    assert reserved is True
    assert count == 42
    assert mock_redis.eval.called

    # 2. Reversão de cota em falha upstream
    await cache.rollback_quota_reservation("WEATHERAPI", shared=True)
    assert mock_redis.eval.call_count == 2


@pytest.mark.asyncio
async def test_clima_cache_quota_limit_exceeded():
    """Testa rejeição atômica quando limite da franquia é atingido."""
    cache = ClimaCache(redis_url="redis://localhost:6379/0")
    mock_redis = AsyncMock()
    # Script Lua retorna {0, current} quando current >= limit
    mock_redis.eval = AsyncMock(return_value=[0, 100000])
    cache.redis = mock_redis

    reserved, count = await cache.reserve_monthly_quota("WEATHERAPI", limit=100000, shared=True)
    assert reserved is False
    assert count == 100000


def test_provider_public_authorization():
    """Garante que provedor alternativo não licenciado não é acionado para o público."""
    with patch.object(settings, "openweather_licensed", False), \
         patch.object(settings, "openweather_allow_unlicensed_public", False):
        assert is_provider_authorized_for_public("OPENWEATHER") is False

    with patch.object(settings, "open_meteo_allow_unlicensed_public", True):
        assert is_provider_authorized_for_public("OPEN_METEO") is True


# ==============================================================================
# 3. TESTES DE ISOLAMENTO DE PLATFORM_CREDENTIALS_MASTER_KEY
# ==============================================================================

def test_master_key_strict_requirement_in_staging_and_production():
    """Garante que staging e produção recusam inicialização sem PLATFORM_CREDENTIALS_MASTER_KEY."""
    with patch.object(settings, "environment", "staging"), \
         patch.object(settings, "platform_credentials_master_key", ""):
        with pytest.raises(RuntimeError) as exc_info:
            PlatformWeatherCredentialsService.validate_master_key_configuration()
        assert "PLATFORM_CREDENTIALS_MASTER_KEY é estritamente obrigatória" in str(exc_info.value)

        with pytest.raises(RuntimeError) as exc_info2:
            _derive_platform_kek(version=2)
        assert "Fallback silencioso para JWT_SECRET_KEY desativado" in str(exc_info2.value)


def test_master_key_allowed_in_development():
    """Em ambiente de desenvolvimento, derivação com fallback emite aviso sem erro fatal."""
    with patch.object(settings, "environment", "development"), \
         patch.object(settings, "platform_credentials_master_key", ""):
        kek = _derive_platform_kek(version=2)
        assert isinstance(kek, bytes)
        assert len(kek) == 32


@pytest.mark.asyncio
async def test_reencrypt_credentials_kek_migration(setup_01h1_env):
    """Testa migração de KEK v1 para KEK v2 com auditoria sem perda de dados."""
    test_key = "test_api_key_weather_secret_12345"

    with patch.object(settings, "environment", "development"):
        # Cifra inicialmente em KEK v1
        v1_encrypted = PlatformWeatherCredentialsService.encrypt_credential(
            provider_slug="WEATHERAPI",
            plaintext_key=test_key,
            key_version=1,
            kek_version=1,
        )
        assert v1_encrypted["kek_version"] == 1

        async with setup_01h1_env() as session:
            rec = ConfiguracaoSaaS(
                chave=KEY_CREDENTIALS_CLIMA,
                valor={
                    "credentials": {
                        "WEATHERAPI": {
                            "ciphertext_b64": v1_encrypted["ciphertext_b64"],
                            "nonce_b64": v1_encrypted["nonce_b64"],
                            "key_version": 1,
                            "kek_version": 1,
                            "masked_key": v1_encrypted["masked_key"],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                            "updated_by": "legacy@deepfarms.com",
                        }
                    },
                    "_meta": {"revision": 1, "version": "1.0"},
                },
                descricao="Credenciais de teste",
                ativo=True,
            )
            session.add(rec)
            await session.commit()

        # Executa migração para KEK v2
        admin_claims = {"sub": str(uuid.uuid4()), "email": "secops@deepfarms.com"}
        async with setup_01h1_env() as session:
            res = await PlatformWeatherCredentialsService.reencrypt_all_credentials_to_canonical_kek(
                session=session,
                admin_claims=admin_claims,
            )
            assert res["migrated_count"] == 1
            assert "WEATHERAPI" in res["providers"]

        # Valida que o registro agora está cifrado em KEK v2 e pode ser decifrado perfeitamente
        async with setup_01h1_env() as session:
            stmt = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_CREDENTIALS_CLIMA)
            record = (await session.execute(stmt)).scalar_one()
            w_cred = record.valor["credentials"]["WEATHERAPI"]
            assert w_cred["kek_version"] == 2

            decrypted = PlatformWeatherCredentialsService.decrypt_credential("WEATHERAPI", w_cred)
            assert decrypted == test_key


# ==============================================================================
# 4. TESTES DA MATRIZ DE HOMOLOGAÇÃO BASEADA EM EVIDÊNCIAS
# ==============================================================================

@pytest.mark.asyncio
async def test_matriz_homologacao_estrita_27_pct(test_app):
    """Verifica se o endpoint de homologação retorna estritamente 3 itens aprovados (27.3%)."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.get("/api/v1/backoffice/agro/dashboard/homologacao")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_itens"] == 11
        assert data["aprovados_count"] == 3
        assert data["em_validacao_count"] == 6
        assert data["pendentes_count"] == 2
        assert data["bloqueados_count"] == 0
        assert data["percentual_conclusao"] == 27.3

        # Itens estritamente aprovados
        aprovados_ids = {item["id"] for item in data["itens"] if item["status"] == "APROVADO"}
        assert aprovados_ids == {5, 10, 11}

        # Itens em validação
        em_val_ids = {item["id"] for item in data["itens"] if item["status"] == "EM VALIDAÇÃO"}
        assert em_val_ids == {1, 2, 3, 4, 8, 9}

        # Itens pendentes de infraestrutura física
        pend_ids = {item["id"] for item in data["itens"] if item["status"] == "PENDENTE"}
        assert pend_ids == {6, 7}


# ==============================================================================
# 5. TESTES DO VALIDADOR DE ISOLAMENTO DE STAGING
# ==============================================================================

def test_validate_staging_config_rejeita_producao():
    """Validador rejeita se ENVIRONMENT ou APP_ENV for production."""
    env = {
        "APP_ENV": "production",
        "ENVIRONMENT": "production",
        "STAGING_DB_HOST": "127.0.0.1",
        "STAGING_DB_PASSWORD": "senha_segura_com_mais_de_16_caracteres",
        "STAGING_REDIS_HOST": "127.0.0.1",
        "STAGING_REDIS_PASSWORD": "senha_segura_com_mais_de_16_caracteres",
        "STAGING_JWT_SECRET_KEY": "jwt_secret_key_com_mais_de_32_caracteres_min",
        "STAGING_PLATFORM_CREDENTIALS_MASTER_KEY": "master_key_com_mais_de_32_caracteres_min",
    }
    errors = validate_staging_config(env)
    assert any("production" in e for e in errors)


def test_validate_staging_config_rejeita_rds_ou_elasticache():
    """Validador rejeita hosts externos de nuvem/produção."""
    env = {
        "APP_ENV": "staging",
        "ENVIRONMENT": "staging",
        "STAGING_DB_HOST": "deepfarms-prod.c4zxxx.us-east-1.rds.amazonaws.com",
        "STAGING_DB_PASSWORD": "senha_segura_com_mais_de_16_caracteres",
        "STAGING_REDIS_HOST": "deepfarms-prod.xxxx.use1.cache.amazonaws.com",
        "STAGING_REDIS_PASSWORD": "senha_segura_com_mais_de_16_caracteres",
        "STAGING_JWT_SECRET_KEY": "jwt_secret_key_com_mais_de_32_caracteres_min",
        "STAGING_PLATFORM_CREDENTIALS_MASTER_KEY": "master_key_com_mais_de_32_caracteres_min",
    }
    errors = validate_staging_config(env)
    assert any("rds.amazonaws.com" in e for e in errors)


def test_validate_staging_config_valido():
    """Validador aceita configuração limpa e estritamente isolada em 127.0.0.1."""
    env = {
        "APP_ENV": "staging",
        "ENVIRONMENT": "staging",
        "STAGING_DB_HOST": "127.0.0.1",
        "STAGING_DB_PASSWORD": "senha_segura_com_mais_de_16_caracteres",
        "STAGING_REDIS_HOST": "127.0.0.1",
        "STAGING_REDIS_PASSWORD": "senha_segura_com_mais_de_16_caracteres",
        "STAGING_JWT_SECRET_KEY": "jwt_secret_key_com_mais_de_32_caracteres_min",
        "STAGING_PLATFORM_CREDENTIALS_MASTER_KEY": "master_key_com_mais_de_32_caracteres_min",
        "S3_BUCKET_NAME": "deepfarms-staging-bucket",
        "S3_ENDPOINT_URL": "http://127.0.0.1:9002",
    }
    errors = validate_staging_config(env)
    assert errors == []
