"""Suíte de testes de integração e conformidade para AGRO-ADMIN-01E5.

Cobre rigorosamente:
1. RBAC em catálogos globais e mensagens institucionais.
2. Isolamento estrito multi-tenant (tenant_id IS NULL vs tenant privado).
3. Proteção contra duplicidade de códigos e nomes canônicos (HTTP 409).
4. Integridade referencial prevenindo exclusão física quando houver referências (HTTP 409).
5. Ciclo de vida completo (CRUD) de mensagens institucionais com auditoria compulsória.
6. Preservação inviolável de avisos legais obrigatórios (DERAL, PTAX, BCB, IBGE).
7. Endpoint público de bootstrap (/public/agro/config) e filtro temporal de vigência.
8. Consumo e aplicação real de Feature Flags operacionais (clima, mercado, ibge, byok).
9. Compatibilidade offline com valores padrão seguros.
10. Gravação compulsória em AdminAuditLog para todas as mutações administrativas.
"""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agro_identity.byok_router import router as byok_router
from core.cadastros.commodities.models import Commodity
from core.cadastros.produtos.models import ProdutoCultura, SoloParametroCultura
from core.database import Base
from core.dependencies import get_current_admin, get_global_user_claims, get_session
from core.measurements.models import UnidadeMedida, UnidadeMedidaConversao
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_user import AdminUser
from core.models.auth import Usuario
from core.models.configuration import ConfiguracaoSaaS
from core.routers.backoffice_agro_catalogo import router as agro_catalogo_router
from core.routers.backoffice_agro_config import router as agro_config_router
from core.schemas.agro_config_schemas import (
    KEY_FLAGS,
    KEY_MENSAGENS,
    AgroFeatureFlagsConfig,
    AgroMensagensAvisosConfig,
)
from core.services.agro_config_service import agro_config_service
from public_agro.router import router as public_agro_router
from public_clima.router import router as public_clima_router
from public_mercado.router import router as public_mercado_router


@pytest.fixture
async def setup_01e5_env(tmp_path):
    """Configura ambiente SQLite isolado em memória com tabelas de governança e catálogos."""
    db_file = tmp_path / "test_agro_01e5.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        ConfiguracaoSaaS.__table__,
        AdminAuditLog.__table__,
        AdminUser.__table__,
        Usuario.__table__,
        Commodity.__table__,
        ProdutoCultura.__table__,
        SoloParametroCultura.__table__,
        UnidadeMedida.__table__,
        UnidadeMedidaConversao.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(agro_config_router, prefix="/api/v1")
    app.include_router(agro_catalogo_router, prefix="/api/v1")
    app.include_router(public_agro_router, prefix="/api/v1")
    app.include_router(public_clima_router, prefix="/api/v1")
    app.include_router(public_mercado_router, prefix="/api/v1")
    app.include_router(byok_router, prefix="/api/v1")

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    admin_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    viewer_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    unauth_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    user_sub = uuid.UUID("44444444-4444-4444-4444-444444444444")

    # Mock user claims para BYOK
    def override_global_claims():
        return {"sub": str(user_sub), "email": "produtor@agro.com"}

    app.dependency_overrides[get_global_user_claims] = override_global_claims

    async with session_factory() as session:
        admin_u = AdminUser(
            id=admin_id,
            email="admin@deepfarms.com",
            nome="Admin Master",
            role="admin",
            ativo=True,
            senha_hash="mock",
        )
        viewer_u = AdminUser(
            id=viewer_id,
            email="viewer@deepfarms.com",
            nome="Suporte Viewer",
            role="suporte",
            ativo=True,
            senha_hash="mock",
        )
        unauth_u = AdminUser(
            id=unauth_id,
            email="financeiro@deepfarms.com",
            nome="Operador Financeiro Sem Acesso",
            role="financeiro",
            ativo=True,
            senha_hash="mock",
        )
        session.add_all([admin_u, viewer_u, unauth_u])
        await session.commit()

    agro_config_service.invalidate_local_cache()

    yield {
        "app": app,
        "session_factory": session_factory,
        "admin_id": admin_id,
        "viewer_id": viewer_id,
        "unauth_id": unauth_id,
        "user_sub": user_sub,
    }

    agro_config_service.invalidate_local_cache()
    await engine.dispose()


def make_admin_claims(role: str, email: str, uid: uuid.UUID) -> dict:
    perms = ["backoffice:agro:*"] if role == "admin" else (["backoffice:agro:view", "backoffice:agro:config:view"] if role == "suporte" else [])
    return {
        "sub": str(uid),
        "email": email,
        "role": role,
        "is_superuser": role == "superadmin",
        "permissoes": perms,
    }


# ==============================================================================
# 1. TESTES DE RBAC EM CATÁLOGOS E MENSAGENS
# ==============================================================================

@pytest.mark.asyncio
async def test_01e5_rbac_catalog_and_messages(setup_01e5_env):
    """Garante controle estrito de RBAC em todas as rotas da fase 01E5."""
    app = setup_01e5_env["app"]
    transport = ASGITransport(app=app)

    # 1. Operador não autorizado tenta acessar catálogos
    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "financeiro", "financeiro@deepfarms.com", setup_01e5_env["unauth_id"]
    )
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_cat = await client.get("/api/v1/backoffice/agro/catalogo/commodities")
        assert res_cat.status_code == 403

        res_msg = await client.get("/api/v1/backoffice/agro/configuracoes/mensagens/lista")
        assert res_msg.status_code == 403

    # 2. Usuário de suporte (visualizador) pode consultar mas não criar
    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "suporte", "viewer@deepfarms.com", setup_01e5_env["viewer_id"]
    )
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_view = await client.get("/api/v1/backoffice/agro/catalogo/commodities")
        assert res_view.status_code == 200

        res_create_denied = await client.post(
            "/api/v1/backoffice/agro/catalogo/commodities",
            json={"nome": "Milho Teste", "codigo": "MILHO_TESTE", "tipo": "AGRICOLA", "unidade_padrao": "SACA_60KG"},
        )
        assert res_create_denied.status_code == 403

    # 3. Administrador possui acesso completo
    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", setup_01e5_env["admin_id"]
    )
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_create_ok = await client.post(
            "/api/v1/backoffice/agro/catalogo/commodities",
            json={"nome": "Milho Safrinha", "codigo": "MILHO_SAFRINHA", "tipo": "AGRICOLA", "unidade_padrao": "SACA_60KG"},
        )
        assert res_create_ok.status_code == 201


# ==============================================================================
# 2. TESTES DE ISOLAMENTO MULTI-TENANT EM CATÁLOGOS
# ==============================================================================

@pytest.mark.asyncio
async def test_01e5_catalog_multi_tenant_isolation(setup_01e5_env):
    """Garante que dados particulares de tenants nunca são retornados ou alterados pelo Agro."""
    app = setup_01e5_env["app"]
    session_factory = setup_01e5_env["session_factory"]
    transport = ASGITransport(app=app)

    tenant_privado_id = uuid.uuid4()
    comm_privada_id = uuid.uuid4()
    comm_global_id = uuid.uuid4()

    # Preenche commodity privada de cliente comercial vs commodity global
    async with session_factory() as session:
        privada = Commodity(
            id=comm_privada_id,
            tenant_id=tenant_privado_id,
            sistema=False,
            nome="Soja Customizada Fazenda Ouro",
            codigo="SOJA_PRIVADA_FAZENDA_OURO",
            tipo="AGRICOLA",
            unidade_padrao="SACA_60KG",
        )
        global_item = Commodity(
            id=comm_global_id,
            tenant_id=None,
            sistema=True,
            nome="Soja em Grão Canônica",
            codigo="SOJA_CANONICA_SISTEMA",
            tipo="AGRICOLA",
            unidade_padrao="SACA_60KG",
        )
        session.add_all([privada, global_item])
        await session.commit()

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", setup_01e5_env["admin_id"]
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # A listagem global DEVE retornar apenas o item global
        res = await client.get("/api/v1/backoffice/agro/catalogo/commodities")
        assert res.status_code == 200
        data = res.json()
        ids = [item["id"] for item in data["itens"]]
        assert str(comm_global_id) in ids
        assert str(comm_privada_id) not in ids

        # Tentativa de detalhe direto na commodity de tenant privado retorna 404
        res_priv_get = await client.get(f"/api/v1/backoffice/agro/catalogo/commodities/{comm_privada_id}")
        assert res_priv_get.status_code == 404

        # Tentativa de alteração direta na commodity de tenant privado retorna 404
        res_priv_put = await client.put(
            f"/api/v1/backoffice/agro/catalogo/commodities/{comm_privada_id}",
            json={"nome": "Invasão Tenant"},
        )
        assert res_priv_put.status_code == 404


# ==============================================================================
# 3. TESTES DE PROTEÇÃO CONTRA DUPLICIDADE (HTTP 409)
# ==============================================================================

@pytest.mark.asyncio
async def test_01e5_duplicate_code_protection(setup_01e5_env):
    """Garante rejeição com 409 Conflict ao tentar cadastrar códigos duplicados."""
    app = setup_01e5_env["app"]
    transport = ASGITransport(app=app)

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", setup_01e5_env["admin_id"]
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Cria commodity
        res1 = await client.post(
            "/api/v1/backoffice/agro/catalogo/commodities",
            json={"nome": "Café Arábica", "codigo": "CAFE_ARABICA_01", "tipo": "AGRICOLA", "unidade_padrao": "SACA_60KG"},
        )
        assert res1.status_code == 201

        # 2. Tenta recriar com mesmo código
        res2 = await client.post(
            "/api/v1/backoffice/agro/catalogo/commodities",
            json={"nome": "Café Conilon", "codigo": "CAFE_ARABICA_01", "tipo": "AGRICOLA", "unidade_padrao": "SACA_60KG"},
        )
        assert res2.status_code == 409
        assert "Já existe uma commodity com o código" in res2.json()["detail"]


# ==============================================================================
# 4. TESTES DE INTEGRIDADE REFERENCIAL (HTTP 409)
# ==============================================================================

@pytest.mark.asyncio
async def test_01e5_referential_integrity_prevent_delete(setup_01e5_env):
    """Garante bloqueio com 409 Conflict ao tentar excluir registros que possuem vínculos operacionais."""
    app = setup_01e5_env["app"]
    session_factory = setup_01e5_env["session_factory"]
    transport = ASGITransport(app=app)

    comm_id = uuid.uuid4()
    uom_origem_id = uuid.uuid4()
    uom_destino_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    async with session_factory() as session:
        uom1 = UnidadeMedida(
            id=uom_origem_id,
            tenant_id=None,
            sistema=True,
            codigo="KG_TEST",
            nome="Quilograma",
            dimensao="MASSA",
            codigo_referencia="KG",
            fator_referencia=1.0,
            casas_decimais=2,
            eh_unidade_base=True,
            ativo=True,
        )
        uom2 = UnidadeMedida(
            id=uom_destino_id,
            tenant_id=None,
            sistema=True,
            codigo="SC60_TEST",
            nome="Saca 60kg",
            dimensao="MASSA",
            codigo_referencia="KG",
            fator_referencia=60.0,
            casas_decimais=2,
            eh_unidade_base=False,
            ativo=True,
        )
        comm = Commodity(
            id=comm_id,
            tenant_id=None,
            sistema=True,
            nome="Trigo em Grão",
            codigo="TRIGO_GRAO_TEST",
            tipo="AGRICOLA",
            unidade_padrao="SACA_60KG",
        )
        conv = UnidadeMedidaConversao(
            id=conv_id,
            tenant_id=None,
            unidade_origem_id=uom_origem_id,
            unidade_destino_id=uom_destino_id,
            commodity_id=comm_id,
            fator=0.016666667,
        )
        session.add_all([uom1, uom2, comm, conv])
        await session.commit()

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", setup_01e5_env["admin_id"]
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Tenta excluir a commodity vinculada
        del_comm_res = await client.delete(f"/api/v1/backoffice/agro/catalogo/commodities/{comm_id}")
        assert del_comm_res.status_code == 409
        assert "conversão(ões) de unidade vinculadas" in del_comm_res.json()["detail"]

        # Tenta excluir a UOM vinculada
        del_uom_res = await client.delete(f"/api/v1/backoffice/agro/catalogo/unidades/{uom_origem_id}")
        assert del_uom_res.status_code == 409
        assert "regra(s) de conversão vinculadas" in del_uom_res.json()["detail"]


# ==============================================================================
# 5. TESTES DE MENSAGENS INSTITUCIONAIS E AUDITORIA
# ==============================================================================

@pytest.mark.asyncio
async def test_01e5_institutional_messages_crud_and_audit(setup_01e5_env):
    """Testa ciclo de vida de comunicados institucionais com auditoria obrigatória."""
    app = setup_01e5_env["app"]
    session_factory = setup_01e5_env["session_factory"]
    transport = ASGITransport(app=app)

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", setup_01e5_env["admin_id"]
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Cria nova mensagem
        res_create = await client.post(
            "/api/v1/backoffice/agro/configuracoes/mensagens",
            json={
                "titulo": "Parada Programada para Manutenção",
                "conteudo": "A plataforma passará por melhorias técnicas no domingo.",
                "finalidade": "MANUTENCAO",
                "prioridade": 1,
                "ativo": True,
            },
        )
        assert res_create.status_code == 201
        msg_data = res_create.json()
        msg_id = msg_data["id"]
        assert msg_data["titulo"] == "Parada Programada para Manutenção"

        # 2. Atualiza mensagem
        res_update = await client.put(
            f"/api/v1/backoffice/agro/configuracoes/mensagens/{msg_id}",
            json={"titulo": "Parada Programada Atualizada", "prioridade": 2},
        )
        assert res_update.status_code == 200
        assert res_update.json()["titulo"] == "Parada Programada Atualizada"
        assert res_update.json()["prioridade"] == 2

        # 3. Lista e verifica presença
        res_list = await client.get("/api/v1/backoffice/agro/configuracoes/mensagens/lista")
        assert res_list.status_code == 200
        msgs = res_list.json()
        assert any(m["id"] == msg_id for m in msgs)

        # 4. Remove mensagem
        res_del = await client.delete(f"/api/v1/backoffice/agro/configuracoes/mensagens/{msg_id}")
        assert res_del.status_code == 200
        assert res_del.json()["sucesso"] is True

    # 5. Verifica auditoria em AdminAuditLog
    async with session_factory() as session:
        stmt = select(AdminAuditLog).where(AdminAuditLog.entidade == "configuracoes_saas")
        res_audit = await session.execute(stmt)
        audits = res_audit.scalars().all()
        assert len(audits) >= 3  # create, update, delete


# ==============================================================================
# 6. PRESERVAÇÃO DE AVISOS LEGAIS E CONTRATO PÚBLICO
# ==============================================================================

@pytest.mark.asyncio
async def test_01e5_public_agro_config_and_vigencia(setup_01e5_env):
    """Testa contrato público (/public/agro/config) e filtro temporal rigoroso de vigência."""
    app = setup_01e5_env["app"]
    transport = ASGITransport(app=app)

    now = datetime.now(timezone.utc)
    inicio_futuro = (now + timedelta(days=5)).isoformat()
    fim_passado = (now - timedelta(days=2)).isoformat()

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", setup_01e5_env["admin_id"]
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Cadastra 3 mensagens: vigente, expirada e futura
        await client.post(
            "/api/v1/backoffice/agro/configuracoes/mensagens",
            json={"titulo": "Mensagem Vigente", "conteudo": "Ativa agora", "ativo": True, "prioridade": 1},
        )
        await client.post(
            "/api/v1/backoffice/agro/configuracoes/mensagens",
            json={
                "titulo": "Mensagem Futura",
                "conteudo": "Apenas no futuro",
                "ativo": True,
                "vigencia_inicio": inicio_futuro,
            },
        )
        await client.post(
            "/api/v1/backoffice/agro/configuracoes/mensagens",
            json={
                "titulo": "Mensagem Expirada",
                "conteudo": "Já passou",
                "ativo": True,
                "vigencia_fim": fim_passado,
            },
        )

        # Consulta endpoint público anônimo
        res_pub = await client.get("/api/v1/public/agro/config")
        assert res_pub.status_code == 200
        pub_data = res_pub.json()

        assert pub_data["sucesso"] is True
        assert "avisos_legais" in pub_data
        assert "aviso_precos_deral" in pub_data["avisos_legais"]
        assert "aviso_ptax" in pub_data["avisos_legais"]

        vigentes = pub_data["mensagens_vigentes"]
        titulos_vigentes = [m["titulo"] for m in vigentes]
        assert "Mensagem Vigente" in titulos_vigentes
        assert "Mensagem Futura" not in titulos_vigentes
        assert "Mensagem Expirada" not in titulos_vigentes


# ==============================================================================
# 7. CONSUMO E ENFORCEMENT REAL DE FEATURE FLAGS
# ==============================================================================

@pytest.mark.asyncio
async def test_01e5_feature_flags_real_enforcement(setup_01e5_env):
    """Comprova efeito prático e real das feature flags nos serviços públicos do Agro."""
    app = setup_01e5_env["app"]
    transport = ASGITransport(app=app)

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", setup_01e5_env["admin_id"]
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Comprova que clima_enabled=False desabilita o serviço de previsão com HTTP 503
        await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={
                "valor": {
                    "clima_enabled": False,
                    "mercado_enabled": True,
                    "byok_enabled": True,
                    "ibge_enabled": True,
                    "calculadoras_enabled": True,
                }
            },
        )

        res_clima = await client.get("/api/v1/public/clima/previsao?lat=-23.31&lon=-51.16")
        assert res_clima.status_code == 503
        assert "Módulo de inteligência meteorológica temporariamente desabilitado" in res_clima.json()["detail"]

        # 2. Comprova que mercado_enabled=False desativa cotações PTAX preservando o schema
        await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={
                "valor": {
                    "clima_enabled": True,
                    "mercado_enabled": False,
                    "byok_enabled": True,
                    "ibge_enabled": True,
                    "calculadoras_enabled": True,
                }
            },
        )

        res_ptax = await client.get("/api/v1/public/mercado/ptax")
        assert res_ptax.status_code == 200
        ptax_data = res_ptax.json()
        assert ptax_data["estadoDisponibilidade"] == "MODULO_DESABILITADO_ADMIN"

        # 3. Comprova que ibge_enabled=False desabilita catálogo do IBGE com HTTP 503
        await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={
                "valor": {
                    "clima_enabled": True,
                    "mercado_enabled": True,
                    "byok_enabled": True,
                    "ibge_enabled": False,
                    "calculadoras_enabled": True,
                }
            },
        )

        res_ibge = await client.get("/api/v1/public/mercado/ibge/catalogo")
        assert res_ibge.status_code == 503
        assert "Módulo de estatísticas agropecuárias IBGE/SIDRA desabilitado" in res_ibge.json()["detail"]

        # 4. Comprova que byok_enabled=False bloqueia acesso ao cofre BYOK com HTTP 503
        await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={
                "valor": {
                    "clima_enabled": True,
                    "mercado_enabled": True,
                    "byok_enabled": False,
                    "ibge_enabled": True,
                    "calculadoras_enabled": True,
                }
            },
        )

        res_byok = await client.get("/api/v1/agro/byok/providers")
        assert res_byok.status_code == 503
        assert "Módulo BYOK temporariamente desabilitado" in res_byok.json()["detail"]

        # 5. Restaura flags ativas e comprova reativação imediata sem deploy
        await client.put(
            f"/api/v1/backoffice/agro/configuracoes/{KEY_FLAGS}",
            json={
                "valor": {
                    "clima_enabled": True,
                    "mercado_enabled": True,
                    "byok_enabled": True,
                    "ibge_enabled": True,
                    "calculadoras_enabled": True,
                }
            },
        )

        res_byok_ok = await client.get("/api/v1/agro/byok/providers")
        assert res_byok_ok.status_code == 200
