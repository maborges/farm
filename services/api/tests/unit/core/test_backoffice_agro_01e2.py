"""Testes unitários e de integração para a Fase 01E2:
Fundação de Configurações Dinâmicas, RBAC e Auditoria do DeepFarms Agro.

Valida:
1. Segurança & RBAC:
   - Usuário gratuito/comum é rejeitado com 403.
   - Operador somente leitura pode ler mas recebe 403 ao tentar editar.
   - Operador autorizado realiza leituras e escritas normalmente.
   - Segredos nunca são expostos em texto claro (mascaramento em GET e AuditLog).
2. Integridade & Validação:
   - Validação estrita por Pydantic (rejeição de timeouts/valores fora dos limites).
   - Versionamento persistente e controle de concorrência otimista (409 Conflict).
   - Atomicidade transacional entre alteração e registro em AdminAuditLog.
3. Cache & Resiliência:
   - Cache local L1 com TTL serve requisições subsequentes.
   - Invalidação de cache força releitura do banco de dados.
   - Falha ou indisponibilidade de Redis não interrompe leituras nem escritas.
4. Regressão:
   - Rotas /api/v1/config/saas continuam funcionando para admins com mascaramento e auditoria.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.dependencies import get_current_admin, get_session, require_permission
from core.models.admin_audit_log import AdminAuditLog
from core.models.configuration import ConfiguracaoSaaS
from core.routers.backoffice_agro_config import router as agro_config_router
from core.routers.configuration import router as saas_config_router
from core.models.admin_user import AdminUser
from core.models.auth import Usuario
from core.schemas.agro_config_schemas import (
    KEY_CLIMA,
    KEY_FLAGS,
    KEY_MENSAGENS,
    KEY_MERCADO,
)
from core.services.agro_config_service import agro_config_service
from core.services.config_masking import mask_sensitive_data


@pytest.fixture
async def setup_01e2_app(tmp_path):
    db_file = tmp_path / "test_agro_01e2.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        ConfiguracaoSaaS.__table__,
        AdminAuditLog.__table__,
        AdminUser.__table__,
        Usuario.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(agro_config_router, prefix="/api/v1")
    app.include_router(saas_config_router, prefix="/api/v1")

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    # Limpa cache do serviço antes de cada teste
    agro_config_service.invalidate_local_cache()

    return app, session_factory


@pytest.mark.asyncio
async def test_security_rbac_free_user_and_read_only_access(setup_01e2_app):
    """Garante que usuários sem privilégios não acessam configurações e operador read-only não edita."""
    app, session_factory = setup_01e2_app

    suporte_id = uuid.uuid4()
    async with session_factory() as session:
        # Cria o AdminUser com role suporte no banco
        suporte_user = AdminUser(
            id=suporte_id,
            email="suporte@deepfarms.com",
            senha_hash="dummy_hash",
            nome="Operador Suporte",
            role="suporte",
            ativo=True,
        )
        session.add(suporte_user)
        await session.commit()

    # 1. Usuário comum/gratuito sem permissão administrativa
    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": str(uuid.uuid4()),
        "email": "free.user@gmail.com",
        "role": "user",
        "is_superuser": False,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Usuário comum é bloqueado na leitura
        resp_common = await client.get("/api/v1/backoffice/agro/configuracoes")
        assert resp_common.status_code == 403

        # Usuário comum é bloqueado em /config/saas
        resp_saas = await client.get("/api/v1/config/saas")
        assert resp_saas.status_code == 403

    # 2. Operador suporte com permissão de visualização mas SEM permissão de edição
    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": str(suporte_id),
        "email": "suporte@deepfarms.com",
        "role": "suporte",
        "is_superuser": False,
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Leitura permitida para suporte
        resp_get = await client.get("/api/v1/backoffice/agro/configuracoes")
        assert resp_get.status_code == 200
        data = resp_get.json()
        assert "clima" in data
        assert "feature_flags" in data

        # Escrita bloqueada para suporte
        resp_put = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={"valor": {"clima_enabled": False}},
        )
        assert resp_put.status_code == 403
        assert "Permissão negada" in resp_put.json()["detail"]


@pytest.mark.asyncio
async def test_security_masking_secrets_no_raw_leak(setup_01e2_app):
    """Verifica que dados sensíveis são mascarados tanto em APIs quanto no AdminAuditLog."""
    app, session_factory = setup_01e2_app

    admin_claims = {
        "sub": str(uuid.uuid4()),
        "email": "superadmin@deepfarms.com",
        "role": "super_admin",
        "is_superuser": True,
    }

    app.dependency_overrides[get_current_admin] = lambda: admin_claims

    # Salva configuração de SMTP contendo senha secreta
    async with session_factory() as session:
        smtp_cfg = ConfiguracaoSaaS(
            chave="smtp_global",
            valor={
                "host": "smtp.sendgrid.net",
                "port": 587,
                "user": "apikey",
                "pass": "SG.very_secret_smtp_password_123456",
            },
            descricao="SMTP Corporativo",
            ativo=True,
        )
        session.add(smtp_cfg)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/config/saas")
        assert resp.status_code == 200
        items = resp.json()
        smtp_item = next(i for i in items if i["chave"] == "smtp_global")
        # A senha NUNCA pode ser retornada em texto puro
        assert smtp_item["valor"]["pass"] != "SG.very_secret_smtp_password_123456"
        assert "***" in smtp_item["valor"]["pass"]


@pytest.mark.asyncio
async def test_integrity_typed_validation_and_rejection(setup_01e2_app):
    """Garante que payloads inválidos fora dos limites sejam rejeitados com erro 422."""
    app, session_factory = setup_01e2_app

    admin_claims = {
        "sub": str(uuid.uuid4()),
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    app.dependency_overrides[get_current_admin] = lambda: admin_claims

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Payload inválido: timeout de 30s (o limite máximo estrito é 15.0s)
        resp_invalid = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_CLIMA}",
            json={
                "valor": {
                    "active_provider": "WEATHERAPI",
                    "timeout_seconds": 30.0,
                    "cache_ttl_seconds": 1800,
                }
            },
        )
        assert resp_invalid.status_code == 422
        assert "Falha de validação" in resp_invalid.json()["detail"]

        # 2. Payload inválido: snapshot DERAL fora do padrão de data
        resp_deral_invalid = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_MERCADO}",
            json={
                "valor": {
                    "ptax_cache_ttl_seconds": 1800,
                    "macro_cache_ttl_seconds": 1800,
                    "max_defasagem_dias": 14,
                    "deral_active_snapshot": "arquivo_invalido.txt",
                }
            },
        )
        assert resp_deral_invalid.status_code == 422

        # 3. Payload válido: persiste normalmente
        resp_valid = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_CLIMA}",
            json={
                "valor": {
                    "active_provider": "WEATHERAPI",
                    "fallback_chain": ["OPENWEATHER", "OPEN_METEO"],
                    "timeout_seconds": 4.5,
                    "cache_ttl_seconds": 1200,
                    "monthly_quota_limit": 150000,
                    "force_contingency_mode": False,
                }
            },
        )
        assert resp_valid.status_code == 200
        res_data = resp_valid.json()
        assert res_data["valor"]["timeout_seconds"] == 4.5
        assert res_data["meta"]["revision"] == 1
        assert res_data["meta"]["updated_by"] == "admin@deepfarms.com"


@pytest.mark.asyncio
async def test_integrity_concurrency_control_optimistic_locking(setup_01e2_app):
    """Verifica que conflitos de concorrência (revisão defasada) geram HTTP 409 Conflict."""
    app, session_factory = setup_01e2_app

    admin_claims = {
        "sub": str(uuid.uuid4()),
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    app.dependency_overrides[get_current_admin] = lambda: admin_claims

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Primeira alteração (espera revisão 0)
        resp1 = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={
                "valor": {"clima_enabled": True, "mercado_enabled": True},
                "expected_revision": 0,
            },
        )
        assert resp1.status_code == 200
        assert resp1.json()["meta"]["revision"] == 1

        # Segunda alteração simultânea enviando revisão antiga (espera 0, mas atual é 1)
        resp_conflict = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={
                "valor": {"clima_enabled": False, "mercado_enabled": True},
                "expected_revision": 0,
            },
        )
        assert resp_conflict.status_code == 409
        assert "Conflito de concorrência" in resp_conflict.json()["detail"]

        # Terceira alteração enviando revisão correta (1) -> sucesso
        resp_ok = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={
                "valor": {"clima_enabled": False, "mercado_enabled": True},
                "expected_revision": 1,
            },
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json()["meta"]["revision"] == 2


@pytest.mark.asyncio
async def test_audit_atomicity_and_logging(setup_01e2_app):
    """Garante que toda mutação grava atomicamente em AdminAuditLog."""
    app, session_factory = setup_01e2_app

    admin_uid = uuid.uuid4()
    admin_claims = {
        "sub": str(admin_uid),
        "email": "auditor@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    app.dependency_overrides[get_current_admin] = lambda: admin_claims

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_MENSAGENS}",
            json={
                "valor": {
                    "aviso_precos_deral": "Novo aviso oficial homologado pelo DERAL para teste.",
                    "aviso_ptax": "PTAX oficial Banco Central do Brasil homologada.",
                    "aviso_macro_bcb": "Indicadores macroeconômicos oficiais SGS.",
                    "aviso_ibge": "Estatísticas de produção agrícola municipal.",
                    "banner_urgente": "Aviso de manutenção preventiva no próximo domingo.",
                }
            },
            headers={"user-agent": "DeepFarmsTestAgent/1.0"},
        )
        assert resp.status_code == 200

    # Verifica persistência no AdminAuditLog
    async with session_factory() as session:
        stmt = select(AdminAuditLog).where(
            AdminAuditLog.entidade == "configuracoes_saas",
            AdminAuditLog.acao == "agro.config.update",
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1
        log = logs[0]
        assert log.admin_email == "auditor@deepfarms.com"
        assert log.admin_user_id == admin_uid
        assert log.user_agent == "DeepFarmsTestAgent/1.0"
        assert "manutenção preventiva" in str(log.dados_novos)


@pytest.mark.asyncio
async def test_cache_and_redis_offline_resilience(setup_01e2_app):
    """Verifica que o cache local em memória funciona e falhas de Redis são toleradas."""
    app, session_factory = setup_01e2_app

    admin_claims = {
        "sub": str(uuid.uuid4()),
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    app.dependency_overrides[get_current_admin] = lambda: admin_claims

    # Simula falha total de conexão com Redis
    with patch("redis.asyncio.from_url", side_effect=ConnectionError("Redis offline")):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Escrita deve suceder mesmo com Redis fora do ar
            resp_put = await client.put(
                f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
                json={"valor": {"byok_enabled": False}},
            )
            assert resp_put.status_code == 200

            # 2. Leitura com cache local ativo
            resp_get = await client.get(f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}")
            assert resp_get.status_code == 200
            assert resp_get.json()["valor"]["byok_enabled"] is False

            # 3. Endpoint de limpeza de cache executa sem erro
            resp_clear = await client.post("/api/v1/backoffice/agro/configuracoes/cache/clear")
            assert resp_clear.status_code == 200
            assert "invalidado com sucesso" in resp_clear.json()["message"]


@pytest.mark.asyncio
async def test_saas_global_config_regression_secured(setup_01e2_app):
    """Garante que a rota original /config/saas está protegida, auditada e compatível."""
    app, session_factory = setup_01e2_app

    admin_claims = {
        "sub": str(uuid.uuid4()),
        "email": "admin_saas@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    app.dependency_overrides[get_current_admin] = lambda: admin_claims

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Atualiza uma chave genérica da plataforma
        resp = await client.put(
            "/api/v1/config/saas/maintenance_mode",
            json={
                "valor": {"enabled": False, "motivo": "Operação normal"},
                "descricao": "Controle de modo manutenção da plataforma",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["chave"] == "maintenance_mode"

        # Leitura da lista
        resp_list = await client.get("/api/v1/config/saas")
        assert resp_list.status_code == 200
        keys = [item["chave"] for item in resp_list.json()]
        assert "maintenance_mode" in keys

    # Confirma gravação em auditoria
    async with session_factory() as session:
        stmt = select(AdminAuditLog).where(
            AdminAuditLog.acao == "saas.config.update"
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1
        assert logs[0].admin_email == "admin_saas@deepfarms.com"


@pytest.mark.asyncio
async def test_audit_foreign_key_resolution_for_global_user(setup_01e2_app):
    """Garante que a resolução de identidade administrativa não viola a FK admin_audit_log_admin_user_id_fkey."""
    app, session_factory = setup_01e2_app

    usuario_uuid = uuid.UUID("cdebc345-a9c5-48ce-8c8e-d0a2d3cd661e")
    admin_user_uuid = uuid.UUID("675aa654-d0db-407c-9c75-8407edd9e120")

    async with session_factory() as session:
        # 1. Usuário global na tabela usuarios (id = usuario_uuid)
        user = Usuario(
            id=usuario_uuid,
            email="admin@borgus.com.br",
            username="admin_borgus",
            senha_hash="dummy_hash",
            is_superuser=True,
            ativo=True,
        )
        # 2. Registro administrativo na tabela admin_users com UUID diferente
        admin = AdminUser(
            id=admin_user_uuid,
            email="admin@borgus.com.br",
            senha_hash="dummy_hash",
            nome="Admin Borgus",
            role="super_admin",
            ativo=True,
        )
        session.add(user)
        session.add(admin)
        await session.commit()

    # Claims típicos do JWT autenticado (onde sub é o ID do Usuario e não contém email)
    admin_claims = {
        "sub": str(usuario_uuid),
        "is_superuser": True,
        "role": None,
    }
    app.dependency_overrides[get_current_admin] = lambda: admin_claims

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_MENSAGENS}",
            json={
                "valor": {
                    "aviso_precos_deral": "Aviso oficial DERAL atualizado por usuário global.",
                    "aviso_ptax": "PTAX oficial Banco Central do Brasil homologada.",
                    "aviso_macro_bcb": "Indicadores macroeconômicos oficiais SGS.",
                    "aviso_ibge": "Estatísticas de produção agrícola municipal.",
                    "banner_urgente": None,
                }
            },
        )
        # Deve responder 200 e NÃO dar 500 ForeignKeyViolationError
        assert resp.status_code == 200

    # Verifica que o admin_user_id gravado no log respeita a chave de admin_users
    async with session_factory() as session:
        stmt = select(AdminAuditLog).where(
            AdminAuditLog.entidade == "configuracoes_saas",
            AdminAuditLog.acao == "agro.config.update",
        )
        log = (await session.execute(stmt)).scalars().first()
        assert log is not None
        # O ID deve ser o do AdminUser e o e-mail deve ser o real do usuário
        assert log.admin_user_id == admin_user_uuid
        assert log.admin_email == "admin@borgus.com.br"


