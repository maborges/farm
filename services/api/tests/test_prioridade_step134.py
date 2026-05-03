"""Step 134 — Testes: priorização comercial das solicitações de IA."""
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
    sol.status = status
    sol.valor_estimado = Decimal(str(valor)) if valor is not None else None
    sol.proximo_followup_em = followup_em
    return sol


# ── base por status ────────────────────────────────────────────────────────────

def test_em_analise_base_50():
    sol = _make("EM_ANALISE")
    assert _calcular_prioridade(sol) == 50


def test_aberta_base_20():
    sol = _make("ABERTA")
    assert _calcular_prioridade(sol) == 20


def test_concluida_base_zero():
    sol = _make("CONCLUIDA")
    assert _calcular_prioridade(sol) == 0


def test_cancelada_penalidade():
    sol = _make("CANCELADA")
    assert _calcular_prioridade(sol) == 0  # clamp: não vai negativo


# ── valor influencia ───────────────────────────────────────────────────────────

def test_valor_100_adiciona_10():
    sol = _make("ABERTA", valor=100.0)
    # 20 (ABERTA) + 10 (100/10) = 30
    assert _calcular_prioridade(sol) == 30


def test_valor_500_adiciona_50_maximo():
    sol = _make("ABERTA", valor=500.0)
    # 20 (ABERTA) + 50 (max) = 70
    assert _calcular_prioridade(sol) == 70


def test_valor_1000_limitado_a_50():
    sol = _make("EM_ANALISE", valor=1000.0)
    # 50 (EM_ANALISE) + 50 (max) = 100
    assert _calcular_prioridade(sol) == 100


# ── follow-up impacta prioridade ──────────────────────────────────────────────

def test_followup_atrasado_adiciona_40():
    now = datetime.now(timezone.utc)
    sol = _make("ABERTA", followup_em=now - timedelta(hours=1))
    # 20 + 40 = 60
    assert _calcular_prioridade(sol) == 60


def test_followup_dentro_de_1h_adiciona_20():
    now = datetime.now(timezone.utc)
    sol = _make("ABERTA", followup_em=now + timedelta(minutes=30))
    # 20 + 20 = 40
    assert _calcular_prioridade(sol) == 40


def test_followup_futuro_longe_nao_impacta():
    now = datetime.now(timezone.utc)
    sol = _make("ABERTA", followup_em=now + timedelta(days=3))
    # 20 + 0 = 20
    assert _calcular_prioridade(sol) == 20


def test_sem_followup_nao_impacta():
    sol = _make("ABERTA")
    assert _calcular_prioridade(sol) == 20


# ── clamp 0–100 ───────────────────────────────────────────────────────────────

def test_clamp_maximo_100():
    now = datetime.now(timezone.utc)
    # EM_ANALISE(50) + valor 500+(50) + followup atrasado(40) = 140 → clamp 100
    sol = _make("EM_ANALISE", valor=600.0, followup_em=now - timedelta(hours=2))
    assert _calcular_prioridade(sol) == 100


def test_clamp_minimo_zero():
    sol = _make("CANCELADA")
    # -20 → clamp 0
    assert _calcular_prioridade(sol) == 0


# ── campo no schema e rota registrada ────────────────────────────────────────

def test_campo_prioridade_no_schema():
    from core.routers.backoffice_ia_auditoria import SolicitacaoItemResponse
    assert "prioridade" in SolicitacaoItemResponse.model_fields


def test_rota_solicitacoes_com_ordenar_por():
    paths = {route.path for route in router.routes}
    assert "/backoffice/ia/creditos/solicitacoes" in paths
