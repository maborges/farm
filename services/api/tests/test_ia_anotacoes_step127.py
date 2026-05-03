"""Step 127 — Testes: anotações comerciais nas solicitações de créditos de IA"""
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock

from core.routers.backoffice_ia_auditoria import (
    SolicitacaoItemResponse,
    StatusUpdatePayload,
    _STATUS_PERMITIDOS,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial


def _make_sol(status: str = "ABERTA", obs: str | None = None):
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.id = uuid.uuid4()
    sol.tenant_id = uuid.uuid4()
    sol.usuario_id = uuid.uuid4()
    sol.tipo = "CREDITOS_IA"
    sol.status = status
    sol.status_pagamento = "PENDENTE"
    sol.valor_estimado = Decimal("10.00")
    sol.observacao_comercial = obs
    sol.created_at = datetime(2026, 5, 2, 10, 0, 0, tzinfo=timezone.utc)
    sol.detalhes = {"quantidade": 100}
    return sol


# ── modelo ────────────────────────────────────────────────────────────────────

def test_solicitacao_model_tem_campo_observacao():
    assert hasattr(SolicitacaoComercial, "observacao_comercial")


# ── SolicitacaoItemResponse ───────────────────────────────────────────────────

def test_response_inclui_observacao_preenchida():
    item = SolicitacaoItemResponse(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        tenant_nome="Fazenda X",
        tipo="CREDITOS_IA",
        status="ABERTA",
        observacao_comercial="Cliente pediu contato na próxima semana.",
        created_at=datetime.now(timezone.utc),
    )
    assert item.observacao_comercial == "Cliente pediu contato na próxima semana."


def test_response_observacao_none_por_padrao():
    item = SolicitacaoItemResponse(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        tenant_nome="Fazenda Y",
        tipo="CREDITOS_IA",
        status="ABERTA",
        created_at=datetime.now(timezone.utc),
    )
    assert item.observacao_comercial is None


# ── StatusUpdatePayload ───────────────────────────────────────────────────────

def test_payload_com_observacao():
    p = StatusUpdatePayload(status="EM_ANALISE", observacao_comercial="Aguardando aprovação interna.")
    assert p.status == "EM_ANALISE"
    assert p.observacao_comercial == "Aguardando aprovação interna."


def test_payload_sem_observacao_none():
    p = StatusUpdatePayload(status="ABERTA")
    assert p.observacao_comercial is None


def test_payload_observacao_vazia_aceita():
    p = StatusUpdatePayload(status="CONCLUIDA", observacao_comercial="")
    assert p.observacao_comercial == ""


# ── lógica de update ──────────────────────────────────────────────────────────

def test_status_update_nao_sobrescreve_obs_se_none():
    sol = _make_sol(obs="Observação existente.")
    payload = StatusUpdatePayload(status="EM_ANALISE")
    # Simula a lógica do endpoint: só atualiza se não for None
    if payload.observacao_comercial is not None:
        sol.observacao_comercial = payload.observacao_comercial
    assert sol.observacao_comercial == "Observação existente."


def test_status_update_sobrescreve_obs_quando_fornecida():
    sol = _make_sol(obs="Obs antiga.")
    payload = StatusUpdatePayload(status="EM_ANALISE", observacao_comercial="Obs nova.")
    if payload.observacao_comercial is not None:
        sol.observacao_comercial = payload.observacao_comercial
    assert sol.observacao_comercial == "Obs nova."


def test_status_update_pode_limpar_obs_com_string_vazia():
    sol = _make_sol(obs="Obs antiga.")
    payload = StatusUpdatePayload(status="CONCLUIDA", observacao_comercial="")
    if payload.observacao_comercial is not None:
        sol.observacao_comercial = payload.observacao_comercial
    assert sol.observacao_comercial == ""


# ── permissão ────────────────────────────────────────────────────────────────

def test_router_tem_permissao():
    from core.routers.backoffice_ia_auditoria import router
    assert len(router.dependencies) > 0
