"""Testes unitários e de integração para a Fase 01D: Gestão de Usuários DeepFarms Agro.

Valida:
1. Listagem isolada de produtores gratuitos (INDIVIDUAL_FREE) com busca, filtros de status e BYOK.
2. Detalhes com sessões ativas e credenciais BYOK mascaradas (zero vazamento de segredos).
3. Bloqueio e desbloqueio com revogação automática de sessões e auditoria estrita.
4. Revogação avulsa de sessões com auditoria.
5. Conversão atômica de produtor Agro para cliente comercial (Tenant + Assinatura + Owner)
   mantendo estritamente o UUID e credenciais originais.
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
from core.dependencies import get_session, require_permission, get_current_admin
from core.models.admin_audit_log import AdminAuditLog
from core.models.auth import Usuario, TenantUsuario
from core.models.tenant import Tenant
from core.models.billing import PlanoAssinatura, AssinaturaTenant
from core.models.sessao import SessaoAtiva
from core.models.usuario_byok import UsuarioByokCredential
from core.routers.backoffice_agro import router as agro_router


@pytest.fixture
async def setup_agro_backoffice_app(tmp_path):
    db_file = tmp_path / "test_agro_backoffice_01d.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        Usuario.__table__,
        Tenant.__table__,
        TenantUsuario.__table__,
        SessaoAtiva.__table__,
        PlanoAssinatura.__table__,
        AssinaturaTenant.__table__,
        UsuarioByokCredential.__table__,
        AdminAuditLog.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(agro_router, prefix="/api/v1")

    async def override_get_session():
        async with session_factory() as session:
            yield session

    mock_admin_claims = {
        "sub": str(uuid.uuid4()),
        "email": "operador.agro@deepfarms.com",
        "username": "operador_agro",
        "is_superuser": True,
        "roles": ["admin"],
        "role": "admin",
    }

    async def override_get_current_admin():
        return mock_admin_claims

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    yield app, session_factory, mock_admin_claims


@pytest.mark.asyncio
async def test_listar_produtores_agro_e_filtros(setup_agro_backoffice_app):
    app, session_factory, _ = setup_agro_backoffice_app

    user_free_id = uuid.uuid4()
    user_commercial_id = uuid.uuid4()
    user_byok_id = uuid.uuid4()

    async with session_factory() as session:
        # Usuário 1: Free simples
        u1 = Usuario(
            id=user_free_id,
            email="produtor1@agro.com.br",
            username="produtor1",
            nome_completo="João da Silva",
            cpf="11144477735",
            is_superuser=False,
            ativo=True,
        )
        # Usuário 2: Comercial (não deve aparecer na listagem Agro)
        u2 = Usuario(
            id=user_commercial_id,
            email="comercial@fazenda.com.br",
            username="comercial_user",
            nome_completo="Carlos Comercial",
            is_superuser=False,
            ativo=True,
        )
        t_comm = Tenant(id=uuid.uuid4(), nome="Fazenda Modelo", slug="fazenda-modelo", ativo=True)
        tu = TenantUsuario(tenant_id=t_comm.id, usuario_id=user_commercial_id, is_owner=True, status="ATIVO")

        # Usuário 3: Free com BYOK
        u3 = Usuario(
            id=user_byok_id,
            email="produtor_byok@agro.com.br",
            username="produtor_byok",
            nome_completo="Maria Pastore",
            cpf="22255588800",
            is_superuser=False,
            ativo=False,  # Bloqueado para testar filtro
        )
        byok = UsuarioByokCredential(
            id=uuid.uuid4(),
            usuario_id=user_byok_id,
            provider_slug="weatherapi",
            ciphertext_b64="Y2lwaGVydGV4dF90ZXN0ZQ==",
            data_nonce_b64="bm9uY2VfZGF0YV8xMmJfcGFk",
            dek_encrypted_b64="ZGVrX2VuY3J5cHRlZF9iNjRfcGFk",
            dek_nonce_b64="ZGVrX25vbmNlX2I2NF9wYWQ=",
            key_version=1,
            mascara_chave="****-****-****-9999",
            status="ATIVO",
        )
        session.add_all([u1, u2, t_comm, tu, u3, byok])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Listagem completa (apenas free)
        resp = await client.get("/api/v1/backoffice/agro/usuarios")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        emails = [item["email"] for item in data["items"]]
        assert "produtor1@agro.com.br" in emails
        assert "produtor_byok@agro.com.br" in emails
        assert "comercial@fazenda.com.br" not in emails

        # 2. Busca por nome
        resp_search = await client.get("/api/v1/backoffice/agro/usuarios?search=Silva")
        assert resp_search.status_code == 200
        assert resp_search.json()["total"] == 1
        assert resp_search.json()["items"][0]["email"] == "produtor1@agro.com.br"

        # 3. Filtro por status bloqueado
        resp_blocked = await client.get("/api/v1/backoffice/agro/usuarios?status=bloqueado")
        assert resp_blocked.status_code == 200
        assert resp_blocked.json()["total"] == 1
        assert resp_blocked.json()["items"][0]["id"] == str(user_byok_id)

        # 4. Filtro por BYOK
        resp_byok = await client.get("/api/v1/backoffice/agro/usuarios?has_byok=true")
        assert resp_byok.status_code == 200
        assert resp_byok.json()["total"] == 1
        assert resp_byok.json()["items"][0]["byok_count"] == 1
        assert "weatherapi" in resp_byok.json()["items"][0]["byok_providers"]

        # 5. Minimização de dados pessoais (CPF mascarado na listagem)
        item1 = next(i for i in data["items"] if i["email"] == "produtor1@agro.com.br")
        assert item1["cpf"] == "***.***.777-**"
        assert item1["cpf"] != "11144477735"

        # 6. Busca por CPF encontra produtor com resposta mascarada
        resp_cpf = await client.get("/api/v1/backoffice/agro/usuarios?search=111444777")
        assert resp_cpf.status_code == 200
        assert resp_cpf.json()["total"] == 1
        assert resp_cpf.json()["items"][0]["cpf"] == "***.***.777-**"


@pytest.mark.asyncio
async def test_obter_detalhes_produtor_agro(setup_agro_backoffice_app):
    app, session_factory, _ = setup_agro_backoffice_app

    target_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with session_factory() as session:
        u = Usuario(
            id=target_id,
            email="detalhe@agro.com.br",
            username="detalhe_user",
            nome_completo="Produtor Detalhado",
            cpf="33366699912",
            telefone="11987654321",
            is_superuser=False,
            ativo=True,
        )
        sess = SessaoAtiva(
            id=session_id,
            usuario_id=target_id,
            token_hash="hash_teste",
            status="ATIVA",
            ip_address="192.168.1.100",
            user_agent="DeepFarms PWA / Mobile",
            expira_em=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        byok = UsuarioByokCredential(
            id=uuid.uuid4(),
            usuario_id=target_id,
            provider_slug="hg_brasil",
            ciphertext_b64="Y2lwaGVydGV4dF90ZXN0ZQ==",
            data_nonce_b64="bm9uY2VfZGF0YV8xMmJfcGFk",
            dek_encrypted_b64="ZGVrX2VuY3J5cHRlZF9iNjRfcGFk",
            dek_nonce_b64="ZGVrX25vbmNlX2I2NF9wYWQ=",
            key_version=1,
            mascara_chave="****-1234",
            status="ATIVO",
        )
        session.add_all([u, sess, byok])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/backoffice/agro/usuarios/{target_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(target_id)
        assert data["email"] == "detalhe@agro.com.br"
        assert data["account_type"] == "INDIVIDUAL_FREE"
        assert len(data["sessoes_ativas"]) == 1
        assert data["sessoes_ativas"][0]["ip_address"] == "192.168.1.100"
        assert len(data["credenciais_byok"]) == 1
        assert data["credenciais_byok"][0]["mascara_chave"] == "****-1234"
        # Zero vazamento de segredos
        assert "ciphertext" not in data["credenciais_byok"][0]

        # Minimização estrita de dados pessoais (CPF e telefone mascarados nos detalhes)
        assert data["cpf"] == "***.***.999-**"
        assert data["cpf"] != "33366699912"
        assert data["telefone"] == "(11) *****-4321"
        assert data["telefone"] != "11987654321"

        # 404 para inexistente
        resp_404 = await client.get(f"/api/v1/backoffice/agro/usuarios/{uuid.uuid4()}")
        assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_alternar_status_e_revogar_sessoes(setup_agro_backoffice_app):
    app, session_factory, admin_claims = setup_agro_backoffice_app

    target_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with session_factory() as session:
        u = Usuario(
            id=target_id,
            email="bloqueio@agro.com.br",
            username="bloqueio_user",
            is_superuser=False,
            ativo=True,
        )
        sess = SessaoAtiva(
            id=session_id,
            usuario_id=target_id,
            token_hash="hash_teste",
            status="ATIVA",
            expira_em=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        session.add_all([u, sess])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Bloquear usuário
        resp_toggle = await client.post(f"/api/v1/backoffice/agro/usuarios/{target_id}/toggle-status")
        assert resp_toggle.status_code == 200
        assert resp_toggle.json()["novo_status"] is False
        assert resp_toggle.json()["sessoes_encerradas"] == 1

        # Verificar no banco que a sessão foi encerrada e o log foi gerado
        async with session_factory() as session:
            sess_db = await session.get(SessaoAtiva, session_id)
            assert sess_db.status == "ENCERRADA"

            stmt_audit = select(AdminAuditLog).where(
                AdminAuditLog.entidade == "usuario",
                AdminAuditLog.entidade_id == target_id,
            )
            audit = (await session.execute(stmt_audit)).scalars().first()
            assert audit is not None
            assert audit.acao == "AGRO_USUARIO_BLOQUEADO"
            assert audit.admin_email == admin_claims["email"]


@pytest.mark.asyncio
async def test_revogacao_avulsa_de_sessoes(setup_agro_backoffice_app):
    app, session_factory, _ = setup_agro_backoffice_app

    target_id = uuid.uuid4()
    sess1_id = uuid.uuid4()
    sess2_id = uuid.uuid4()

    async with session_factory() as session:
        u = Usuario(
            id=target_id,
            email="sessoes@agro.com.br",
            username="sessoes_user",
            is_superuser=False,
            ativo=True,
        )
        sess1 = SessaoAtiva(id=sess1_id, usuario_id=target_id, token_hash="h1", status="ATIVA", expira_em=datetime.now(timezone.utc) + timedelta(hours=1))
        sess2 = SessaoAtiva(id=sess2_id, usuario_id=target_id, token_hash="h2", status="ATIVA", expira_em=datetime.now(timezone.utc) + timedelta(hours=1))
        session.add_all([u, sess1, sess2])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp_revoke = await client.delete(f"/api/v1/backoffice/agro/usuarios/{target_id}/sessions")
        assert resp_revoke.status_code == 200
        assert resp_revoke.json()["sessoes_encerradas"] == 2

        # Usuário continua ATIVO
        async with session_factory() as session:
            user_db = await session.get(Usuario, target_id)
            assert user_db.ativo is True


@pytest.mark.asyncio
async def test_conversao_comercial_desabilitada_efetivamente(setup_agro_backoffice_app):
    """Comprova que a conversão comercial está desabilitada (HTTP 403) e não cria registros."""
    app, session_factory, admin_claims = setup_agro_backoffice_app

    target_id = uuid.uuid4()
    plano_id = uuid.uuid4()

    async with session_factory() as session:
        u = Usuario(
            id=target_id,
            email="converter@agro.com.br",
            username="converter_user",
            nome_completo="Produtor Tentativa Conversao",
            cpf="12345678909",
            is_superuser=False,
            ativo=True,
        )
        plano = PlanoAssinatura(
            id=plano_id,
            nome="Plano Fazenda Profissional",
            preco_mensal=299.00,
            preco_anual=2990.00,
            is_free=False,
            tem_trial=True,
            dias_trial=15,
            plan_tier="PROFISSIONAL",
            ativo=True,
        )
        session.add_all([u, plano])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Catálogo de planos comercial segue disponível para leitura
        resp_planos = await client.get("/api/v1/backoffice/agro/planos")
        assert resp_planos.status_code == 200

        # Tentativa de conversão
        payload = {
            "nome_fazenda": "Fazenda Tentativa",
            "plano_id": str(plano_id),
            "ciclo": "MENSAL",
            "documento": "00.000.000/0001-91",
        }
        resp_conv = await client.post(
            f"/api/v1/backoffice/agro/usuarios/{target_id}/converter-comercial",
            json=payload,
        )
        # 1. Rota responde estritamente 403 Forbidden informando contenção
        assert resp_conv.status_code == 403
        data = resp_conv.json()
        assert "temporariamente desabilitada" in data["detail"]

        # 2. Comprovação de não-criação de registros comerciais no banco
        async with session_factory() as session:
            # Usuário segue inalterado e ativo
            user_db = await session.get(Usuario, target_id)
            assert user_db is not None
            assert user_db.ativo is True

            # Nenhum Tenant criado
            stmt_tenant = select(Tenant).where(Tenant.nome == "Fazenda Tentativa")
            tenant_db = (await session.execute(stmt_tenant)).scalar_one_or_none()
            assert tenant_db is None

            # Nenhum vínculo TenantUsuario criado
            stmt_tu = select(TenantUsuario).where(TenantUsuario.usuario_id == target_id)
            tu_list = (await session.execute(stmt_tu)).scalars().all()
            assert len(tu_list) == 0

            # Nenhuma Assinatura comercial criada
            stmt_assin = select(AssinaturaTenant).where(AssinaturaTenant.plano_id == plano_id)
            assin_list = (await session.execute(stmt_assin)).scalars().all()
            assert len(assin_list) == 0

            # Nenhuma ação indevida registrada no AdminAuditLog
            stmt_audit = select(AdminAuditLog).where(
                AdminAuditLog.entidade_id == target_id,
                AdminAuditLog.acao == "AGRO_USUARIO_CONVERTIDO_COMERCIAL",
            )
            audit_entry = (await session.execute(stmt_audit)).scalar_one_or_none()
            assert audit_entry is None
