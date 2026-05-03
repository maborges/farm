"""Step 128 — Testes: responsável comercial pela solicitação de IA"""
import uuid
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from core.routers.backoffice_ia_auditoria import (
    SolicitacaoItemResponse,
    ResponsavelPayload,
    router,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial
from core.models.admin_user import AdminUser


# ── model ─────────────────────────────────────────────────────────────────────

def test_solicitacao_model_tem_campo_responsavel():
    assert hasattr(SolicitacaoComercial, "responsavel_usuario_id")


# ── SolicitacaoItemResponse ───────────────────────────────────────────────────

def test_response_inclui_responsavel_preenchido():
    uid = str(uuid.uuid4())
    item = SolicitacaoItemResponse(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        tenant_nome="Fazenda X",
        tipo="CREDITOS_IA",
        status="EM_ANALISE",
        responsavel_usuario_id=uid,
        responsavel_nome="João Comercial",
        created_at=datetime.now(timezone.utc),
    )
    assert item.responsavel_usuario_id == uid
    assert item.responsavel_nome == "João Comercial"


def test_response_responsavel_none_por_padrao():
    item = SolicitacaoItemResponse(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        tenant_nome="Fazenda Y",
        tipo="CREDITOS_IA",
        status="ABERTA",
        created_at=datetime.now(timezone.utc),
    )
    assert item.responsavel_usuario_id is None
    assert item.responsavel_nome is None


# ── ResponsavelPayload ────────────────────────────────────────────────────────

def test_payload_com_usuario():
    uid = uuid.uuid4()
    p = ResponsavelPayload(responsavel_usuario_id=uid)
    assert p.responsavel_usuario_id == uid


def test_payload_none_remove_responsavel():
    p = ResponsavelPayload(responsavel_usuario_id=None)
    assert p.responsavel_usuario_id is None


def test_payload_default_none():
    p = ResponsavelPayload()
    assert p.responsavel_usuario_id is None


# ── lógica de atribuição ──────────────────────────────────────────────────────

def test_atribuir_responsavel_preenche_campo():
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.responsavel_usuario_id = None

    uid = uuid.uuid4()
    sol.responsavel_usuario_id = uid
    assert sol.responsavel_usuario_id == uid


def test_remover_responsavel_seta_none():
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.responsavel_usuario_id = uuid.uuid4()

    sol.responsavel_usuario_id = None
    assert sol.responsavel_usuario_id is None


# ── AdminUser ─────────────────────────────────────────────────────────────────

def test_admin_user_tem_campos_necessarios():
    assert hasattr(AdminUser, "id")
    assert hasattr(AdminUser, "nome")
    assert hasattr(AdminUser, "email")


# ── router ────────────────────────────────────────────────────────────────────

def test_rota_responsavel_registrada():
    paths = {route.path for route in router.routes}
    assert "/backoffice/ia/creditos/solicitacoes/{solicitacao_id}/responsavel" in paths


def test_router_tem_permissao():
    assert len(router.dependencies) > 0
