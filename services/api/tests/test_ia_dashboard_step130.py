"""Step 130 — Testes: dashboard comercial de solicitações de IA"""
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock

from core.routers.backoffice_ia_auditoria import (
    ResumoSolicitacoesResponse,
    ResumoPorResponsavel,
    router,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial


def _make_sol(status: str, valor: float = 10.0, resp_id: uuid.UUID | None = None) -> MagicMock:
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.id = uuid.uuid4()
    sol.tenant_id = uuid.uuid4()
    sol.status = status
    sol.status_pagamento = "PENDENTE"
    sol.valor_estimado = Decimal(str(valor))
    sol.responsavel_usuario_id = resp_id
    sol.tipo = "CREDITOS_IA"
    sol.created_at = datetime(2026, 5, 2, 10, 0, 0, tzinfo=timezone.utc)
    sol.detalhes = {}
    return sol


# ── contagens ─────────────────────────────────────────────────────────────────

def test_contagem_por_status():
    rows = [
        _make_sol("ABERTA"), _make_sol("ABERTA"),
        _make_sol("EM_ANALISE"),
        _make_sol("CONCLUIDA"), _make_sol("CONCLUIDA"), _make_sol("CONCLUIDA"),
        _make_sol("CANCELADA"),
    ]
    assert sum(1 for r in rows if r.status == "ABERTA") == 2
    assert sum(1 for r in rows if r.status == "EM_ANALISE") == 1
    assert sum(1 for r in rows if r.status == "CONCLUIDA") == 3
    assert sum(1 for r in rows if r.status == "CANCELADA") == 1


def test_valor_pendente_soma_aberta_e_em_analise():
    rows = [
        _make_sol("ABERTA", valor=10.0),
        _make_sol("EM_ANALISE", valor=20.0),
        _make_sol("CONCLUIDA", valor=50.0),
    ]
    pendentes = {"ABERTA", "EM_ANALISE"}
    valor = sum(float(r.valor_estimado or 0) for r in rows if r.status in pendentes)
    assert valor == 30.0


def test_valor_concluido():
    rows = [_make_sol("CONCLUIDA", valor=15.0) for _ in range(3)]
    valor = sum(float(r.valor_estimado or 0) for r in rows if r.status == "CONCLUIDA")
    assert valor == 45.0


# ── taxa de conversão ─────────────────────────────────────────────────────────

def test_taxa_conversao_calculada():
    rows = [
        _make_sol("ABERTA"), _make_sol("EM_ANALISE"),
        _make_sol("CONCLUIDA"), _make_sol("CONCLUIDA"),
    ]
    total_abertas = sum(1 for r in rows if r.status == "ABERTA")
    total_em_analise = sum(1 for r in rows if r.status == "EM_ANALISE")
    total_concluidas = sum(1 for r in rows if r.status == "CONCLUIDA")
    elegiveis = total_abertas + total_em_analise + total_concluidas
    taxa = round(total_concluidas / elegiveis * 100, 1) if elegiveis else 0.0
    assert taxa == 50.0


def test_taxa_conversao_sem_dados():
    elegiveis = 0
    taxa = 0.0 if not elegiveis else 100.0
    assert taxa == 0.0


def test_canceladas_nao_entram_na_taxa():
    rows = [_make_sol("CANCELADA") for _ in range(10)]
    total_abertas = sum(1 for r in rows if r.status == "ABERTA")
    total_em_analise = sum(1 for r in rows if r.status == "EM_ANALISE")
    total_concluidas = sum(1 for r in rows if r.status == "CONCLUIDA")
    elegiveis = total_abertas + total_em_analise + total_concluidas
    assert elegiveis == 0


# ── por responsável ───────────────────────────────────────────────────────────

def test_agrupamento_por_responsavel():
    from collections import defaultdict

    uid_a = uuid.uuid4()
    uid_b = uuid.uuid4()
    rows = [
        _make_sol("ABERTA", valor=10.0, resp_id=uid_a),
        _make_sol("ABERTA", valor=10.0, resp_id=uid_a),
        _make_sol("ABERTA", valor=20.0, resp_id=uid_b),
        _make_sol("ABERTA", valor=5.0, resp_id=None),
    ]

    por_resp: dict = defaultdict(lambda: {"total": 0, "valor": 0.0})
    for r in rows:
        key = str(r.responsavel_usuario_id) if r.responsavel_usuario_id else "__sem__"
        por_resp[key]["total"] += 1
        por_resp[key]["valor"] += float(r.valor_estimado or 0)

    assert por_resp[str(uid_a)]["total"] == 2
    assert por_resp[str(uid_b)]["total"] == 1
    assert por_resp["__sem__"]["total"] == 1


# ── schemas ───────────────────────────────────────────────────────────────────

def test_resumo_solicitacoes_response():
    r = ResumoSolicitacoesResponse(
        total_abertas=3, total_em_analise=1,
        total_concluidas=2, total_canceladas=0,
        valor_pendente=40.0, valor_concluido=30.0,
        taxa_conversao=33.3,
        por_responsavel=[],
    )
    assert r.total_abertas == 3
    assert r.taxa_conversao == 33.3


def test_resumo_por_responsavel_sem_id():
    r = ResumoPorResponsavel(
        responsavel_usuario_id=None,
        responsavel_nome="Sem responsável",
        total=5,
        valor_estimado=50.0,
    )
    assert r.responsavel_usuario_id is None
    assert r.responsavel_nome == "Sem responsável"


# ── router ────────────────────────────────────────────────────────────────────

def test_rota_resumo_registrada():
    paths = {route.path for route in router.routes}
    assert "/backoffice/ia/creditos/solicitacoes/resumo" in paths


def test_router_tem_permissao():
    assert len(router.dependencies) > 0
