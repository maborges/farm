"""Testes unitários do fluxo público de solicitação de demonstração na landing page."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.constants import DEMO_TENANT_CANONICAL_NAME
from core.database import Base
from core.dependencies import get_session
from core.models.auth import ConviteAcesso, PerfilAcesso, TenantUsuario, Usuario
from core.models.configuration import ConfiguracaoSaaS
from core.models.crm import AtividadeCRM, LeadCRM, PipelineEstagio
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from core.routers.onboarding import router as onboarding_router
from core.services.auth_service import hash_password
from core.services.demo_config_service import invalidate_demo_config_cache
from core.services.demo_request_rate_limit import DemoRequestRateLimiter
from core.services.email_service import email_service


@pytest.fixture
async def demo_request_app(tmp_path, monkeypatch):
    """Configura app FastAPI isolado em SQLite temporário para testar /onboarding/demonstracao/solicitar."""
    db_file = tmp_path / "test_demo_public_request.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        Usuario.__table__,
        Tenant.__table__,
        ConfiguracaoSaaS.__table__,
        PerfilAcesso.__table__,
        TenantUsuario.__table__,
        ConviteAcesso.__table__,
        UnidadeProdutiva.__table__,
        PipelineEstagio.__table__,
        LeadCRM.__table__,
        AtividadeCRM.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    send_invite_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(email_service, "send_invite", send_invite_mock)

    invalidate_demo_config_cache()
    await DemoRequestRateLimiter.reset_for_tests()

    app = FastAPI()
    app.include_router(onboarding_router, prefix="/api/v1")

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with session_factory() as session:
        demo_tenant = Tenant(
            id=uuid.uuid4(),
            nome=DEMO_TENANT_CANONICAL_NAME,
            slug="produtor-deepfarms-demo",
            documento="11111111000111",
            ativo=True,
            is_demo=True,
        )
        session.add(demo_tenant)
        await session.flush()

        fazenda_ativa = UnidadeProdutiva(
            id=uuid.uuid4(),
            tenant_id=demo_tenant.id,
            nome="Fazenda Modelo",
            ativo=True,
        )
        session.add(fazenda_ativa)
        await session.commit()

        yield {
            "app": app,
            "session_factory": session_factory,
            "demo_tenant_id": demo_tenant.id,
            "fazenda_id": fazenda_ativa.id,
            "send_invite_mock": send_invite_mock,
        }

    await DemoRequestRateLimiter.reset_for_tests()
    invalidate_demo_config_cache()
    await engine.dispose()


@pytest.mark.asyncio
async def test_novo_usuario_solicita_demonstracao_cria_convite_e_lead_sem_expor_token(demo_request_app):
    """Visitante novo recebe 202, gera convite demo, lead no CRM e e-mail sem token na resposta."""
    app = demo_request_app["app"]
    session_factory = demo_request_app["session_factory"]
    send_invite_mock = demo_request_app["send_invite_mock"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/onboarding/demonstracao/solicitar",
            json={
                "nome": "João Produtor",
                "email": "joao.novo@fazenda.com.br",
                "telefone": "64999990000",
                "empresa": "Fazenda Esperança",
            },
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["ja_cadastrado"] is False
    assert body["ja_vinculado_demo"] is False
    assert body["convite_reenviado"] is False
    assert body["dias_acesso"] == 15
    assert "token" not in body
    assert "token_convite" not in body
    send_invite_mock.assert_awaited_once()

    async with session_factory() as session:
        convite = (
            await session.execute(
                select(ConviteAcesso).where(ConviteAcesso.email_convidado == "joao.novo@fazenda.com.br")
            )
        ).scalar_one()
        assert convite.status == "PENDENTE"
        assert str(demo_request_app["fazenda_id"]) in (convite.unidades_produtivas_ids or [])

        lead = (
            await session.execute(select(LeadCRM).where(LeadCRM.email == "joao.novo@fazenda.com.br"))
        ).scalar_one()
        assert lead.origem == "demonstracao"


@pytest.mark.asyncio
async def test_usuario_ja_cadastrado_recebe_aviso_e_email_de_confirmacao(demo_request_app):
    """Usuário já existente fora do tenant demo recebe aviso específico e e-mail de confirmação."""
    app = demo_request_app["app"]
    session_factory = demo_request_app["session_factory"]
    send_invite_mock = demo_request_app["send_invite_mock"]

    async with session_factory() as session:
        session.add(
            Usuario(
                id=uuid.uuid4(),
                email="maria.existente@agro.com.br",
                username="maria_existente",
                nome_completo="Maria Existente",
                senha_hash=hash_password("SenhaForte123!"),
                ativo=True,
            )
        )
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/onboarding/demonstracao/solicitar",
            json={"nome": "Maria Existente", "email": "maria.existente@agro.com.br"},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["ja_cadastrado"] is True
    assert body["ja_vinculado_demo"] is False
    assert "já está cadastrado" in body["mensagem"].lower()
    assert "confirmação" in body["mensagem"].lower()
    send_invite_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_usuario_ja_vinculado_ao_demo_nao_gera_novo_convite(demo_request_app):
    """Usuário já vinculado ao tenant de demonstração é orientado a fazer login sem novo convite."""
    app = demo_request_app["app"]
    session_factory = demo_request_app["session_factory"]
    send_invite_mock = demo_request_app["send_invite_mock"]

    async with session_factory() as session:
        user_id = uuid.uuid4()
        session.add(
            Usuario(
                id=user_id,
                email="carlos.demo@agro.com.br",
                username="carlos_demo",
                nome_completo="Carlos Demo",
                senha_hash=hash_password("SenhaForte123!"),
                ativo=True,
            )
        )
        session.add(
            TenantUsuario(
                tenant_id=demo_request_app["demo_tenant_id"],
                usuario_id=user_id,
                status="ATIVO",
            )
        )
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/onboarding/demonstracao/solicitar",
            json={"nome": "Carlos Demo", "email": "carlos.demo@agro.com.br"},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["ja_cadastrado"] is True
    assert body["ja_vinculado_demo"] is True
    assert "login" in body["mensagem"].lower()
    send_invite_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_solicitacao_repetida_reutiliza_convite_pendente(demo_request_app):
    """Solicitação repetida para o mesmo e-mail reutiliza o convite pendente sem duplicar."""
    app = demo_request_app["app"]
    session_factory = demo_request_app["session_factory"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/api/v1/onboarding/demonstracao/solicitar",
            json={"nome": "Ana Repetida", "email": "ana.repetida@agro.com.br"},
        )
        second = await client.post(
            "/api/v1/onboarding/demonstracao/solicitar",
            json={"nome": "Ana Repetida", "email": "ana.repetida@agro.com.br"},
        )

    assert first.status_code == 202
    assert first.json()["convite_reenviado"] is False
    assert second.status_code == 202
    assert second.json()["convite_reenviado"] is True

    async with session_factory() as session:
        convites = (
            await session.execute(
                select(ConviteAcesso).where(ConviteAcesso.email_convidado == "ana.repetida@agro.com.br")
            )
        ).scalars().all()
        assert len(convites) == 1


@pytest.mark.asyncio
async def test_rate_limit_bloqueia_excesso_de_solicitacoes(demo_request_app):
    """Excesso de tentativas pelo mesmo IP retorna 429 com header Retry-After."""
    app = demo_request_app["app"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for idx in range(5):
            ok_resp = await client.post(
                "/api/v1/onboarding/demonstracao/solicitar",
                json={"nome": f"Visitante {idx}", "email": f"visitante{idx}@agro.com.br"},
            )
            assert ok_resp.status_code == 202

        blocked_resp = await client.post(
            "/api/v1/onboarding/demonstracao/solicitar",
            json={"nome": "Visitante Bloqueado", "email": "bloqueado@agro.com.br"},
        )

    assert blocked_resp.status_code == 429
    assert "retry-after" in blocked_resp.headers
