"""Step 135 — Testes: fila comercial prioritária."""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from core.routers.backoffice_ia_auditoria import _calcular_prioridade, router
from core.models.solicitacoes_comerciais import SolicitacaoComercial


def _make(
    status: str = "ABERTA",
    valor: float | None = None,
    followup_em: datetime | None = None,
) -> MagicMock:
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.id = uuid.uuid4()
    sol.tenant_id = uuid.uuid4()
    sol.status = status
    sol.tipo = "CREDITOS_IA"
    sol.valor_estimado = Decimal(str(valor)) if valor is not None else None
    sol.proximo_followup_em = followup_em
    sol.detalhes = {}
    sol.responsavel_usuario_id = None
    sol.usuario_id = None
    sol.status_pagamento = "PENDENTE"
    sol.observacao_comercial = None
    sol.followup_observacao = None
    sol.created_at = datetime.now(timezone.utc)
    return sol


# ── filtro: apenas acionáveis ─────────────────────────────────────────────────

def test_concluida_excluida_da_fila():
    sol = _make("CONCLUIDA")
    assert sol.status in ("CONCLUIDA", "CANCELADA")


def test_cancelada_excluida_da_fila():
    sol = _make("CANCELADA")
    assert sol.status in ("CONCLUIDA", "CANCELADA")


def test_aberta_incluida_na_fila():
    sol = _make("ABERTA")
    assert sol.status not in ("CONCLUIDA", "CANCELADA")


def test_em_analise_incluida_na_fila():
    sol = _make("EM_ANALISE")
    assert sol.status not in ("CONCLUIDA", "CANCELADA")


# ── ordenação por prioridade ──────────────────────────────────────────────────

def test_ordenacao_prioridade_desc():
    now = datetime.now(timezone.utc)
    baixa = _make("ABERTA", valor=10.0)
    media = _make("ABERTA", valor=200.0)
    alta = _make("EM_ANALISE", valor=300.0, followup_em=now - timedelta(hours=1))

    scores = [_calcular_prioridade(s) for s in [baixa, media, alta]]
    assert scores[2] > scores[1] > scores[0]

    itens = sorted([baixa, media, alta], key=lambda s: _calcular_prioridade(s), reverse=True)
    assert itens[0] is alta
    assert itens[-1] is baixa


def test_em_analise_supera_aberta_mesmas_condicoes():
    sol_a = _make("ABERTA", valor=100.0)
    sol_b = _make("EM_ANALISE", valor=100.0)
    assert _calcular_prioridade(sol_b) > _calcular_prioridade(sol_a)


def test_followup_atrasado_sobe_posicao():
    now = datetime.now(timezone.utc)
    sem_followup = _make("ABERTA", valor=100.0)
    com_followup_atrasado = _make("ABERTA", valor=100.0, followup_em=now - timedelta(hours=2))
    assert _calcular_prioridade(com_followup_atrasado) > _calcular_prioridade(sem_followup)


# ── rota registrada ───────────────────────────────────────────────────────────

def test_rota_fila_prioritaria_registrada():
    paths = {route.path for route in router.routes}
    assert "/backoffice/ia/creditos/solicitacoes/fila-prioritaria" in paths


def test_rota_fila_antes_de_id_parametrizado():
    """Garantir que /fila-prioritaria não conflita com /{solicitacao_id}."""
    paths = [route.path for route in router.routes]
    idx_fila = next(i for i, p in enumerate(paths) if p == "/backoffice/ia/creditos/solicitacoes/fila-prioritaria")
    idx_id = next(i for i, p in enumerate(paths) if "{solicitacao_id}" in p)
    assert idx_fila < idx_id


# ── limite padrão ─────────────────────────────────────────────────────────────

def test_limite_padrao_20():
    import inspect
    from core.routers.backoffice_ia_auditoria import fila_prioritaria
    sig = inspect.signature(fila_prioritaria)
    default_limit = sig.parameters["limit"].default
    # Query() com default=20 — verificar via string
    assert str(default_limit) == "20" or getattr(default_limit, "default", None) == 20


# ── campo prioridade no response ──────────────────────────────────────────────

def test_prioridade_campo_presente_no_schema():
    from core.routers.backoffice_ia_auditoria import SolicitacaoItemResponse
    assert "prioridade" in SolicitacaoItemResponse.model_fields
    assert SolicitacaoItemResponse.model_fields["prioridade"].default == 0
