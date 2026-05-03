"""Step 132 — Testes: follow-up comercial das solicitações de IA"""
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from core.routers.backoffice_ia_auditoria import (
    SolicitacaoItemResponse,
    FollowupPayload,
    router,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial


# ── model ─────────────────────────────────────────────────────────────────────

def test_solicitacao_model_tem_campos_followup():
    assert hasattr(SolicitacaoComercial, "proximo_followup_em")
    assert hasattr(SolicitacaoComercial, "followup_observacao")


# ── SolicitacaoItemResponse ───────────────────────────────────────────────────

def test_response_inclui_followup_preenchido():
    dt = datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc)
    item = SolicitacaoItemResponse(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        tenant_nome="Fazenda X",
        tipo="CREDITOS_IA",
        status="EM_ANALISE",
        proximo_followup_em=dt,
        followup_observacao="Ligar amanhã",
        created_at=datetime.now(timezone.utc),
    )
    assert item.proximo_followup_em == dt
    assert item.followup_observacao == "Ligar amanhã"


def test_response_followup_none_por_padrao():
    item = SolicitacaoItemResponse(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        tenant_nome="Fazenda Y",
        tipo="CREDITOS_IA",
        status="ABERTA",
        created_at=datetime.now(timezone.utc),
    )
    assert item.proximo_followup_em is None
    assert item.followup_observacao is None


# ── FollowupPayload ───────────────────────────────────────────────────────────

def test_payload_com_dados():
    dt = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)
    p = FollowupPayload(proximo_followup_em=dt, followup_observacao="Reunião agendada")
    assert p.proximo_followup_em == dt
    assert p.followup_observacao == "Reunião agendada"


def test_payload_limpeza():
    p = FollowupPayload(proximo_followup_em=None, followup_observacao=None)
    assert p.proximo_followup_em is None
    assert p.followup_observacao is None


# ── router ────────────────────────────────────────────────────────────────────

def test_rota_followup_registrada():
    paths = {route.path for route in router.routes}
    assert "/backoffice/ia/creditos/solicitacoes/{solicitacao_id}/followup" in paths


def test_router_tem_permissao():
    assert len(router.dependencies) > 0
