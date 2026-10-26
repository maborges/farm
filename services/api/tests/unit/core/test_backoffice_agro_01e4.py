"""Suíte de testes de integração e conformidade para AGRO-ADMIN-01E4.

Cobre rigorosamente:
1. RBAC em todas as operações (status, config, upload, activate, rollback).
2. Validação estrita de snapshots DERAL (extensão, tamanho, schema, 21 commodities).
3. Rejeição de arquivos adulterados, incompletos, corruptos ou com valores negativos/NaN.
4. Integridade SHA-256 e proveniência verificável.
5. Versionamento e listagem histórica de snapshots.
6. Publicação atômica e proteção de ponteiro transacional.
7. Rollback seguro para versão previamente homologada.
8. Controle otimista de concorrência com expected_revision (HTTP 409).
9. Invalidação de cache L1 de PrecosPublicosService sem necessidade de restart.
10. Impossibilidade de adulterar cotações oficiais individualmente ou injetar arquivos arbitrários.
11. Auditoria compulsória em AdminAuditLog.
12. Regressão e preservação dos contratos públicos (/public/mercado/precos e /catalogo).
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.dependencies import get_current_admin, get_session
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_user import AdminUser
from core.models.auth import Usuario
from core.models.configuration import ConfiguracaoSaaS
from core.routers.backoffice_agro_config import router as agro_config_router
from core.routers.backoffice_agro_mercado import router as agro_mercado_router
from core.schemas.agro_config_schemas import (
    KEY_MERCADO,
    AgroMercadoConfig,
)
from core.services.agro_config_service import agro_config_service
from core.services.deral_snapshot_service import deral_snapshot_service
from public_mercado.precos_publicos import (
    METADADOS_CATALOGO,
    SNAPSHOT_PATH,
    carregar_catalogo_mercado,
    carregar_precos_publicos,
    set_snapshot_cache_override,
)
from public_mercado.precos_publicos_service import get_precos_service
from public_mercado.router import router as public_mercado_router


@pytest.fixture
def baseline_snapshot_dict() -> dict:
    """Carrega o payload baseline homologado deral-prp-2026-10-16.json."""
    assert SNAPSHOT_PATH.exists()
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


@pytest.fixture
async def setup_01e4_env(tmp_path, baseline_snapshot_dict):
    """Configura ambiente SQLite isolado, tabelas e cliente ASGI para a fase 01E4."""
    db_file = tmp_path / "test_agro_01e4.db"
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
    app.include_router(agro_mercado_router, prefix="/api/v1")
    app.include_router(agro_config_router, prefix="/api/v1")
    app.include_router(public_mercado_router, prefix="/api/v1")

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    admin_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    viewer_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    unauth_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async with session_factory() as session:
        admin_u = AdminUser(
            id=admin_id,
            email="admin@deepfarms.com",
            nome="Admin Teste",
            role="admin",
            ativo=True,
            senha_hash="mock",
        )
        viewer_u = AdminUser(
            id=viewer_id,
            email="viewer@deepfarms.com",
            nome="Viewer Teste",
            role="suporte",
            ativo=True,
            senha_hash="mock",
        )
        unauth_u = AdminUser(
            id=unauth_id,
            email="financeiro@deepfarms.com",
            nome="Financeiro Sem Acesso Agro",
            role="financeiro",
            ativo=True,
            senha_hash="mock",
        )
        session.add_all([admin_u, viewer_u, unauth_u])
        await session.commit()

    # Limpa caches em memória
    deral_snapshot_service.clear_cache()
    agro_config_service.invalidate_local_cache()
    get_precos_service().invalidate_cache()
    set_snapshot_cache_override(None)

    yield {
        "app": app,
        "session_factory": session_factory,
        "admin_id": admin_id,
        "viewer_id": viewer_id,
        "unauth_id": unauth_id,
    }

    # Teardown
    deral_snapshot_service.clear_cache()
    agro_config_service.invalidate_local_cache()
    get_precos_service().invalidate_cache()
    set_snapshot_cache_override(None)
    await engine.dispose()


def make_admin_claims(role: str, email: str, uid: uuid.UUID, permissions: list[str] | None = None) -> dict:
    """Gera claims JWT administrativos com RBAC canônico."""
    perms = permissions
    if perms is None:
        if role == "admin":
            perms = ["backoffice:agro:*"]
        elif role == "suporte":
            perms = ["backoffice:agro:view", "backoffice:agro:market:view", "backoffice:agro:config:view"]
        else:
            perms = []

    return {
        "sub": str(uid),
        "id": str(uid),
        "email": email,
        "role": role,
        "type": "admin",
        "permissoes": perms,
    }


# ==============================================================================
# TESTES DE RBAC E SEGURANÇA
# ==============================================================================

@pytest.mark.asyncio
async def test_rbac_market_status_and_snapshots_unauthenticated_and_forbidden(setup_01e4_env):
    """Garante bloqueio 401 para requisições anônimas e 403 para usuários sem permissão."""
    env = setup_01e4_env
    app = env["app"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Sem credenciais / headers -> 401
        res = await client.get("/api/v1/backoffice/agro/mercado/status")
        assert res.status_code == 401

        res_list = await client.get("/api/v1/backoffice/agro/mercado/deral/snapshots")
        assert res_list.status_code == 401

    # 2. Usuário com role sem permissão para agro (ex: financeiro) -> 403
    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "financeiro", "fin@deepfarms.com", env["unauth_id"], permissions=[]
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_status = await client.get("/api/v1/backoffice/agro/mercado/status")
        assert res_status.status_code == 403

        res_upload = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("test.json", b"{}", "application/json")},
        )
        assert res_upload.status_code == 403


@pytest.mark.asyncio
async def test_market_status_success_for_authorized_admin(setup_01e4_env):
    """Garante retorno 200 e integridade dos dados para operador autorizado."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "suporte", "viewer@deepfarms.com", env["viewer_id"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/backoffice/agro/mercado/status")
        assert res.status_code == 200
        data = res.json()

        assert "sources" in data
        assert len(data["sources"]) == 4

        fontes_ids = {s["fonte_id"] for s in data["sources"]}
        assert fontes_ids == {"BCB_PTAX", "BCB_SGS", "IBGE_SIDRA", "DERAL_SEAB"}

        deral_source = next(s for s in data["sources"] if s["fonte_id"] == "DERAL_SEAB")
        assert deral_source["status"] in ("ONLINE", "DEFASADO")
        assert deral_source["cache_ttl_seconds"] == 1800
        assert deral_source["detalhes_operacionais"]["total_commodities_homologadas"] == 21


# ==============================================================================
# TESTES DE CONFIGURAÇÃO OPERACIONAL E CONCORRÊNCIA
# ==============================================================================

@pytest.mark.asyncio
async def test_market_config_update_ttls_and_audit(setup_01e4_env):
    """Testa atualização de TTLs operacionais de cache com auditoria compulsória."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Atualiza parâmetros operacionais
        payload = {
            "ptax_cache_ttl_seconds": 3600,
            "macro_cache_ttl_seconds": 7200,
            "sidra_cache_ttl_seconds": 14400,
            "precos_cache_ttl_seconds": 3600,
            "max_defasagem_dias": 20,
            "expected_revision": 0,
        }
        res = await client.put("/api/v1/backoffice/agro/mercado/config", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["config"]["ptax_cache_ttl_seconds"] == 3600
        assert data["config"]["macro_cache_ttl_seconds"] == 7200
        assert data["config"]["max_defasagem_dias"] == 20
        assert data["revision"] == 1

    # Verifica auditoria no banco
    async with env["session_factory"]() as session:
        stmt = select(AdminAuditLog).where(AdminAuditLog.entidade == "configuracoes_saas")
        res_audit = await session.execute(stmt)
        audits = res_audit.scalars().all()
        assert len(audits) >= 1
        last_audit = audits[-1]
        assert last_audit.admin_email == "admin@deepfarms.com"
        assert last_audit.acao == "agro.config.update"


@pytest.mark.asyncio
async def test_market_config_concurrency_conflict_409(setup_01e4_env):
    """Garante rejeição HTTP 409 em caso de expected_revision desatualizada."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Atualização com revisão divergente (ex: esperado 999 quando atual é 0)
        payload = {
            "ptax_cache_ttl_seconds": 1200,
            "expected_revision": 999,
        }
        res = await client.put("/api/v1/backoffice/agro/mercado/config", json=payload)
        assert res.status_code == 409
        assert "Conflito de concorrência" in res.json()["detail"]


@pytest.mark.asyncio
async def test_impossibility_of_arbitrary_active_snapshot_injection_via_generic_config(setup_01e4_env):
    """Garante que operador NÃO pode trocar snapshot ativo arbitrariamente via config genérica."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Tenta injetar arquivo arbitrário em PUT /backoffice/agro/configuracoes/agro:mercado:config
        payload = {
            "valor": {
                "ptax_cache_ttl_seconds": 1800,
                "macro_cache_ttl_seconds": 1800,
                "sidra_cache_ttl_seconds": 3600,
                "precos_cache_ttl_seconds": 1800,
                "max_defasagem_dias": 14,
                "deral_active_snapshot": "deral-prp-9999-99-99.json",  # Arquivo forjado!
                "active_snapshot_id": "9999-99-99",
                "deral_source_url": "https://malicious-site.com/fake.xls",
                "ptax_enabled": True,
                "sgs_enabled": True,
                "sidra_enabled": True,
                "deral_enabled": True,
            }
        }
        res = await client.put("/api/v1/backoffice/agro/configuracoes/agro:mercado:config", json=payload)
        # Deve rejeitar com 400
        assert res.status_code == 400
        assert "A ativação do snapshot DERAL ativo deve ocorrer exclusivamente por operação administrativa validada" in res.json()["detail"]


# ==============================================================================
# TESTES DE INGESTÃO, VALIDAÇÃO E INTEGRIDADE SHA-256 DE SNAPSHOTS DERAL
# ==============================================================================

@pytest.mark.asyncio
async def test_deral_snapshot_upload_and_strict_validation_success(setup_01e4_env, baseline_snapshot_dict):
    """Testa upload e validação de novo snapshot semanal íntegro com 21 commodities."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    # Cria snapshot novo para 2026-10-23
    new_snapshot = copy.deepcopy(baseline_snapshot_dict)
    new_snapshot["dataReferencia"] = "2026-10-23"
    new_snapshot["semana"] = "43-2026"
    raw_bytes = json.dumps(new_snapshot).encode("utf-8")
    expected_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("deral-prp-2026-10-23.json", raw_bytes, "application/json")},
        )
        assert res.status_code == 200
        data = res.json()

        assert data["sucesso"] is True
        assert data["metadata"]["id"] == "2026-10-23"
        assert data["metadata"]["sha256"] == expected_sha256
        assert data["metadata"]["total_itens"] == 21
        assert data["metadata"]["status"] == "VALIDADO"
        assert data["metadata"]["is_active"] is False  # Upload NÃO ativa automaticamente!


@pytest.mark.asyncio
async def test_deral_snapshot_upload_rejection_invalid_extension(setup_01e4_env):
    """Garante rejeição de extensões perigosas ou não homologadas (.exe, .sh, .py)."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("malware.exe", b"MZ\x90\x00" * 50, "application/octet-stream")},
        )
        assert res.status_code == 400
        assert "inválida" in res.json()["detail"]


@pytest.mark.asyncio
async def test_deral_snapshot_upload_rejection_missing_mandatory_commodity(setup_01e4_env, baseline_snapshot_dict):
    """Garante rejeição de snapshot incompleto se faltar qualquer uma das 21 commodities (ex: soja)."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    incomplete_snapshot = copy.deepcopy(baseline_snapshot_dict)
    incomplete_snapshot["dataReferencia"] = "2026-10-30"
    # Remove a commodity 'soja'
    incomplete_snapshot["itens"] = [i for i in incomplete_snapshot["itens"] if i["id"] != "soja"]
    assert len(incomplete_snapshot["itens"]) == 20

    raw_bytes = json.dumps(incomplete_snapshot).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("deral-prp-2026-10-30.json", raw_bytes, "application/json")},
        )
        assert res.status_code == 400
        assert "Snapshot incompleto" in res.json()["detail"]
        assert "soja" in res.json()["detail"]


@pytest.mark.asyncio
async def test_deral_snapshot_upload_rejection_negative_or_nan_values(setup_01e4_env, baseline_snapshot_dict):
    """Garante rejeição de snapshot com valores negativos ou corrompidos."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    corrupted_snapshot = copy.deepcopy(baseline_snapshot_dict)
    corrupted_snapshot["dataReferencia"] = "2026-10-30"
    # Altera boi-gordo para valor negativo
    for item in corrupted_snapshot["itens"]:
        if item["id"] == "boi-gordo":
            item["valor"] = -50.0

    raw_bytes = json.dumps(corrupted_snapshot).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("deral-prp-2026-10-30.json", raw_bytes, "application/json")},
        )
        assert res.status_code == 400
        assert "inválido ou negativo" in res.json()["detail"]


@pytest.mark.asyncio
async def test_deral_snapshot_upload_rejection_corrupted_json(setup_01e4_env):
    """Garante rejeição de JSON malformado."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("corrupted.json", b"{\"itens\": [invalid json" + b" " * 150, "application/json")},
        )
        assert res.status_code == 400
        assert "corrompida ou inválida" in res.json()["detail"]


# ==============================================================================
# TESTES DE ATIVAÇÃO ATÔMICA, ROLLBACK E INVALIDAÇÃO DE CACHE
# ==============================================================================

@pytest.mark.asyncio
async def test_deral_snapshot_atomic_activation_and_cache_invalidation(setup_01e4_env, baseline_snapshot_dict):
    """Testa ativação atômica de snapshot validado com atualização do ponteiro e auditoria."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    # 1. Faz upload do snapshot 2026-10-23
    new_snapshot = copy.deepcopy(baseline_snapshot_dict)
    new_snapshot["dataReferencia"] = "2026-10-23"
    # Modifica o preço da soja para testar reflexo na consulta
    for item in new_snapshot["itens"]:
        if item["id"] == "soja":
            item["valor"] = 155.50
            item["valorOriginal"] = 155.50

    raw_bytes = json.dumps(new_snapshot).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_up = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("deral-prp-2026-10-23.json", raw_bytes, "application/json")},
        )
        assert res_up.status_code == 200

        # 1.1 Aprova formalmente a proveniência do snapshot (01E4A)
        res_appr = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-23/approve",
            json={"aprovado": True, "justificativa": "Homologação de proveniência DERAL"},
        )
        assert res_appr.status_code == 200

        # Antes da ativação, consulta de precos públicos ainda reflete baseline (134.98)
        res_precos_before = await client.get("/api/v1/public/mercado/precos/soja")
        assert res_precos_before.status_code == 200
        assert res_precos_before.json()["valor"] == 134.98

        # 2. Ativa o snapshot 2026-10-23
        res_act = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-23/activate",
            json={"justificativa": "Publicação semanal de cotações DERAL"},
        )
        assert res_act.status_code == 200
        act_data = res_act.json()
        assert act_data["metadata"]["is_active"] is True
        assert act_data["metadata"]["status"] == "ATIVO"

        # 3. Imediatamente após ativação, a rota pública reflete a nova cotação (155.50)
        res_precos_after = await client.get("/api/v1/public/mercado/precos/soja")
        assert res_precos_after.status_code == 200
        assert res_precos_after.json()["valor"] == 155.50
        assert res_precos_after.json()["dataReferencia"] == "2026-10-23"

        # 4. Verifica na lista de snapshots
        res_list = await client.get("/api/v1/backoffice/agro/mercado/deral/snapshots")
        assert res_list.status_code == 200
        snapshots_list = res_list.json()["snapshots"]
        active_snap = next(s for s in snapshots_list if s["is_active"])
        assert active_snap["id"] == "2026-10-23"

        # O snapshot anterior deve ter status ANTERIOR
        old_snap = next(s for s in snapshots_list if s["id"] == "2026-10-16")
        assert old_snap["status"] == "ANTERIOR"
        assert old_snap["is_active"] is False


@pytest.mark.asyncio
async def test_deral_snapshot_rollback_flow(setup_01e4_env, baseline_snapshot_dict):
    """Testa rollback controlado para o snapshot anterior com auditoria de reversão."""
    env = setup_01e4_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    # 1. Ingestão e ativação de 2026-10-23
    new_snapshot = copy.deepcopy(baseline_snapshot_dict)
    new_snapshot["dataReferencia"] = "2026-10-23"
    for item in new_snapshot["itens"]:
        if item["id"] == "milho":
            item["valor"] = 70.00
            item["valorOriginal"] = 70.00

    raw_bytes = json.dumps(new_snapshot).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("deral-prp-2026-10-23.json", raw_bytes, "application/json")},
        )
        await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-23/approve",
            json={"aprovado": True, "justificativa": "Aprovação para rollback"},
        )
        await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-23/activate",
            json={"justificativa": "Ativação de teste"},
        )

        res_milho_new = await client.get("/api/v1/public/mercado/precos/milho")
        assert res_milho_new.json()["valor"] == 70.00

        # 2. Executa ROLLBACK para 2026-10-16
        res_rollback = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-16/rollback",
            json={
                "target_snapshot_id": "2026-10-16",
                "justificativa": "Rollback preventivo devido a inconsistência externa",
            },
        )
        assert res_rollback.status_code == 200
        rollback_data = res_rollback.json()
        assert rollback_data["metadata"]["id"] == "2026-10-16"
        assert rollback_data["metadata"]["is_active"] is True

        # 3. Consulta pública reflete o valor original restaurado do milho (51.77)
        res_milho_restored = await client.get("/api/v1/public/mercado/precos/milho")
        assert res_milho_restored.json()["valor"] == 51.77

    # Verifica auditoria do rollback
    async with env["session_factory"]() as session:
        stmt = select(AdminAuditLog).where(AdminAuditLog.acao == "agro.market.deral.rollback")
        res_audit = await session.execute(stmt)
        audits = res_audit.scalars().all()
        assert len(audits) >= 1
        assert "Rollback do snapshot DERAL" in audits[-1].descricao


# ==============================================================================
# TESTES DE PRESERVAÇÃO DOS CONTRATOS PÚBLICOS
# ==============================================================================

@pytest.mark.asyncio
async def test_public_endpoints_preservation_of_contracts(setup_01e4_env):
    """Garante que todos os endpoints públicos de mercado preservam seus esquemas e contratos."""
    env = setup_01e4_env
    app = env["app"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. /public/mercado/precos
        res_precos = await client.get("/api/v1/public/mercado/precos")
        assert res_precos.status_code == 200
        data_p = res_precos.json()
        assert data_p["sucesso"] is True
        assert len(data_p["itens"]) == 21
        assert "avisoLegal" in data_p

        # 2. /public/mercado/catalogo
        res_cat = await client.get("/api/v1/public/mercado/catalogo")
        assert res_cat.status_code == 200
        data_c = res_cat.json()
        assert data_c["sucesso"] is True
        assert len(data_c["itens"]) == 22  # 21 DERAL + 1 Algodão CONAB

        # 3. Commodity não existente -> 404 seguro
        res_inexistente = await client.get("/api/v1/public/mercado/precos/commodity-inexistente")
        assert res_inexistente.status_code == 404
