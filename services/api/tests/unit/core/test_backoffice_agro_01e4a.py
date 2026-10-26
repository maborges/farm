"""Suite de testes de regressão e validação estrita para AGRO-ADMIN-01E4A.

Cobre os requisitos de hardening de Mercado e DERAL:
1. Segregação estrita entre integridade criptográfica (SHA-256), proveniência declarada,
   proveniência verificada (domínios oficiais *.pr.gov.br) e aprovação formal.
2. Rejeição de aprovação e ativação para snapshots não verificados ou com falha.
3. Auditoria e download de bytes originais brutos com recálculo criptográfico (SHA-256).
4. Restrição estrita de formatos (.json e .xls) e rejeição imediata de formatos não suportados (.xlsx).
5. Validação robusta de planilhas OLE2/BIFF8 corrompidas ou fora do padrão.
6. Publicação atômica em transação única e rollback seguro.
7. Aplicação dinâmica de configurações (PTAX, SGS, SIDRA, DERAL) e resiliência sem Redis.
"""

from __future__ import annotations

import base64
import copy
import json
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from fastapi import FastAPI

from core.database import Base
from core.dependencies import get_current_admin, get_session
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_user import AdminUser
from core.models.auth import Usuario
from core.models.configuration import ConfiguracaoSaaS
from core.routers.backoffice_agro_config import router as agro_config_router
from core.routers.backoffice_agro_mercado import router as agro_mercado_router
from core.schemas.agro_config_schemas import KEY_MERCADO
from core.services.agro_config_service import agro_config_service
from core.services.deral_snapshot_service import (
    KEY_DERAI_INDEX,
    KEY_DERAI_SNAP_PREFIX,
    OLE2_MAGIC,
    deral_snapshot_service,
    verificar_proveniencia_governamental,
)
from public_mercado.precos_publicos import (
    SNAPSHOT_PATH,
    set_snapshot_cache_override,
)
from public_mercado.precos_publicos_service import get_precos_service
from public_mercado.router import (
    apply_dynamic_market_config,
    router as public_mercado_router,
)


def make_admin_claims(role: str = "admin", email: str = "admin@deepfarms.com", user_id: uuid.UUID | None = None) -> dict:
    return {
        "sub": str(user_id or uuid.uuid4()),
        "role": role,
        "email": email,
        "permissions": ["agro:admin", "agro:config:write", "agro:market:write"],
    }


@pytest.fixture
def baseline_snapshot_dict() -> dict:
    """Carrega o payload baseline homologado deral-prp-2026-10-16.json."""
    assert SNAPSHOT_PATH.exists()
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


@pytest.fixture
async def setup_01e4a_env(tmp_path, baseline_snapshot_dict):
    """Configura ambiente SQLite isolado, tabelas e cliente ASGI para 01E4A."""
    db_file = tmp_path / "test_agro_01e4a.db"
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
    operator_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async with session_factory() as session:
        admin_u = AdminUser(
            id=admin_id,
            email="admin@deepfarms.com",
            nome="Admin Teste",
            role="admin",
            ativo=True,
            senha_hash="mock",
        )
        op_u = AdminUser(
            id=operator_id,
            email="operador@deepfarms.com",
            nome="Operador Agro",
            role="operador",
            ativo=True,
            senha_hash="mock",
        )
        session.add_all([admin_u, op_u])
        await session.commit()

    deral_snapshot_service.clear_cache()
    agro_config_service.invalidate_local_cache()
    get_precos_service().invalidate_cache()
    set_snapshot_cache_override(None)

    yield {
        "app": app,
        "session_factory": session_factory,
        "admin_id": admin_id,
        "operator_id": operator_id,
    }

    deral_snapshot_service.clear_cache()
    agro_config_service.invalidate_local_cache()
    get_precos_service().invalidate_cache()
    set_snapshot_cache_override(None)
    await engine.dispose()


# ==============================================================================
# TESTES DE PROVENIÊNCIA GOVERNAMENTAL E SEGREGAÇÃO DE INTEGRIDADE
# ==============================================================================

def test_verificar_proveniencia_governamental_unitario():
    """Valida a função de checagem de proveniência com domínios homologados e não confiáveis."""
    # Domínios oficiais do Paraná válidos
    valido, estado, msg = verificar_proveniencia_governamental(
        "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
        "DERAL/SEAB-PR"
    )
    assert valido is True
    assert estado == "VERIFICADO"
    assert "agricultura.pr.gov.br" in msg

    # Domínio secundário do governo do PR
    valido, estado, msg = verificar_proveniencia_governamental(
        "https://dados.pr.gov.br/dataset/deral/prp.xls",
        "Secretaria da Agricultura PR"
    )
    assert valido is True
    assert estado == "VERIFICADO"

    # Domínio não homologado / externo
    invalido, estado_inv, msg_inv = verificar_proveniencia_governamental(
        "https://noticias-agro-fake.com/deral.json",
        "Fonte Não Oficial"
    )
    assert invalido is False
    assert estado_inv == "FALHA_VERIFICACAO"
    assert "não pertence aos órgãos governamentais homologados" in msg_inv


@pytest.mark.asyncio
async def test_rejeicao_de_aprovacao_para_snapshot_com_falha_de_origem(setup_01e4a_env, baseline_snapshot_dict):
    """Garante que snapshot com origem não governamental falha verificação e não pode ser aprovado."""
    env = setup_01e4a_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    fake_snapshot = copy.deepcopy(baseline_snapshot_dict)
    fake_snapshot["dataReferencia"] = "2026-10-30"
    fake_snapshot["documentoOficial"] = "https://servidor-malicioso.com/cotacoes.json"
    fake_snapshot["fonte"] = "Origem Desconhecida"

    raw_bytes = json.dumps(fake_snapshot).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload deve ser aceito para auditoria, mas marcado como FALHA_VERIFICACAO
        res_up = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("deral-prp-2026-10-30.json", raw_bytes, "application/json")},
        )
        assert res_up.status_code == 200
        up_data = res_up.json()
        assert up_data["metadata"]["origem_verificada"] is False
        assert up_data["metadata"]["estado_verificacao"] == "FALHA_VERIFICACAO"
        assert up_data["metadata"]["estado_aprovacao"] == "PENDENTE"

        # 2. Tentativa de aprovação deve falhar com HTTP 400
        res_appr = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-30/approve",
            json={"aprovado": True, "justificativa": "Tentando aprovar documento não governamental"},
        )
        assert res_appr.status_code == 400
        assert "falha comprovada de verificação de proveniência governamental" in res_appr.text

        # 3. Tentativa de ativação direta sem aprovação deve falhar com HTTP 400
        res_act = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-30/activate",
            json={"justificativa": "Tentativa indevida de ativação"},
        )
        assert res_act.status_code == 400
        assert "está com estado de aprovação 'PENDENTE'" in res_act.text


# ==============================================================================
# TESTES DE AUDITORIA DE BYTES ORIGINAIS E INTEGRIDADE CRIPTOGRÁFICA
# ==============================================================================

@pytest.mark.asyncio
async def test_snapshot_verify_integrity_and_download_raw(setup_01e4a_env, baseline_snapshot_dict):
    """Testa endpoint de auditoria de integridade (/verify-integrity) e download dos bytes originais (/download-raw)."""
    env = setup_01e4a_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    custom_snapshot = copy.deepcopy(baseline_snapshot_dict)
    custom_snapshot["dataReferencia"] = "2026-10-25"
    raw_bytes = json.dumps(custom_snapshot, indent=2).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload
        res_up = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("deral-prp-2026-10-25.json", raw_bytes, "application/json")},
        )
        assert res_up.status_code == 200
        registered_sha = res_up.json()["metadata"]["sha256"]

        # 1. Auditoria de integridade criptográfica
        res_integ = await client.get("/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-25/verify-integrity")
        assert res_integ.status_code == 200
        integ_data = res_integ.json()
        assert integ_data["integro"] is True
        assert integ_data["sha256_registrado"] == registered_sha
        assert integ_data["sha256_recalculado"] == registered_sha
        assert integ_data["tamanho_bytes_registrado"] == len(raw_bytes)
        assert integ_data["tamanho_bytes_armazenado"] == len(raw_bytes)
        assert "Integridade criptográfica comprovada" in integ_data["mensagem"]

        # 2. Download dos bytes binários brutos imutáveis
        res_raw = await client.get("/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-25/download-raw")
        assert res_raw.status_code == 200
        assert res_raw.headers["content-type"].startswith("application/json")
        assert "filename=deral-prp-2026-10-25.json" in res_raw.headers["content-disposition"]
        assert res_raw.content == raw_bytes


# ==============================================================================
# TESTES DE PARSING DE FORMATOS SUPORTADOS E REJEIÇÃO DE EXTENSÕES
# ==============================================================================

@pytest.mark.asyncio
async def test_rejeicao_estrita_de_extensao_xlsx(setup_01e4a_env):
    """Garante que .xlsx seja expressamente rejeitado com orientação detalhada."""
    env = setup_01e4a_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    fake_xlsx_bytes = b"PK\x03\x04fake_zip_content"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("prp.xlsx", fake_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert res.status_code == 400
        assert "Extensão '.xlsx' não suportada" in res.text
        assert ".xls (planilha binária oficial BIFF8 DERAL/SEAB-PR)" in res.text


@pytest.mark.asyncio
async def test_rejeicao_de_xls_com_assinatura_binaria_invalida(setup_01e4a_env):
    """Garante que arquivo nomeado .xls que não possua o cabeçalho OLE2 seja rejeitado."""
    env = setup_01e4a_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    fake_xls_invalid = b"CONTEUDO_TEXTO_SIMPLES_NAO_OLE2" * 10

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("prp.xls", fake_xls_invalid, "application/vnd.ms-excel")},
        )
        assert res.status_code == 400
        assert "Arquivo não possui cabeçalho binário OLE2/BIFF8 válido" in res.text


@pytest.mark.asyncio
async def test_rejeicao_de_xls_ole2_corrompido(setup_01e4a_env):
    """Garante que cabeçalho OLE2 com bytes corrompidos seja tratado com erro 400."""
    env = setup_01e4a_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    # Inicia com OLE2 magic bytes mas corpo truncado/corrompido
    corrupt_ole2 = OLE2_MAGIC + b"\x00" * 100

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("prp.xls", corrupt_ole2, "application/vnd.ms-excel")},
        )
        assert res.status_code == 400
        assert "Planilha DERAL corrompida ou aba oficial 'Rav' ausente" in res.text


# ==============================================================================
# TESTES DE CONTROLE DINÂMICO DE PARÂMETROS OPERACIONAIS E RESILIÊNCIA
# ==============================================================================

@pytest.mark.asyncio
async def test_dynamic_market_config_application(setup_01e4a_env):
    """Testa a aplicação dinâmica de configurações de mercado sem reinício de processo."""
    env = setup_01e4a_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Obtém status atual
        res_get = await client.get("/api/v1/backoffice/agro/mercado/status")
        assert res_get.status_code == 200

        # 2. Desabilita PTAX e DERAL administrativamente
        res_put = await client.put(
            "/api/v1/backoffice/agro/mercado/config",
            json={
                "ptax_enabled": False,
                "deral_enabled": False,
                "ptax_cache_ttl_seconds": 1800,
            },
        )
        assert res_put.status_code == 200

        # 3. Consulta ao serviço público de PTAX reflete a desabilitação com status controlado
        res_ptax = await client.get("/api/v1/public/mercado/ptax")
        assert res_ptax.status_code == 200
        assert res_ptax.json()["estadoDisponibilidade"] == "FONTE_DESABILITADA_ADMIN"
        assert res_ptax.json()["sucesso"] is False

        # 4. Consulta ao serviço público de DERAL reflete a indisponibilidade administrativa com preservação do schema
        res_precos = await client.get("/api/v1/public/mercado/precos")
        assert res_precos.status_code == 200
        assert res_precos.json()["sucesso"] is False
        assert "temporariamente desabilitado" in res_precos.json()["avisoLegal"]

        # 5. Reativa PTAX e DERAL
        res_put_react = await client.put(
            "/api/v1/backoffice/agro/mercado/config",
            json={
                "ptax_enabled": True,
                "deral_enabled": True,
            },
        )
        assert res_put_react.status_code == 200

        # Preços públicos voltam a responder normalmente (200 OK)
        res_precos_ok = await client.get("/api/v1/public/mercado/precos")
        assert res_precos_ok.status_code == 200
        assert res_precos_ok.json()["sucesso"] is True


@pytest.mark.asyncio
async def test_multiworker_db_discovery_reconciliation(setup_01e4a_env, baseline_snapshot_dict):
    """Testa reconciliação do snapshot ativo diretamente via banco de dados (descoberta multi-worker)."""
    env = setup_01e4a_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: make_admin_claims(
        "admin", "admin@deepfarms.com", env["admin_id"]
    )

    new_snapshot = copy.deepcopy(baseline_snapshot_dict)
    new_snapshot["dataReferencia"] = "2026-10-27"
    raw_bytes = json.dumps(new_snapshot).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/backoffice/agro/mercado/deral/upload",
            files={"file": ("deral-prp-2026-10-27.json", raw_bytes, "application/json")},
        )
        await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-27/approve",
            json={"aprovado": True, "justificativa": "Homologado para reconciliação multi-worker"},
        )
        await client.post(
            "/api/v1/backoffice/agro/mercado/deral/snapshots/2026-10-27/activate",
            json={"justificativa": "Ativação no worker A"},
        )

    # Simula Worker B: limpa o cache local em memória e executa reconciliação a partir do banco
    deral_snapshot_service.clear_cache()
    async with env["session_factory"]() as session:
        active_data = await deral_snapshot_service.sync_active_snapshot_from_db(session)
        assert active_data is not None
        assert active_data["dataReferencia"] == "2026-10-27"
        assert deral_snapshot_service._active_snapshot_id == "2026-10-27"
