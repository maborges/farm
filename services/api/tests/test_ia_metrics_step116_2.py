"""
Step 116.2 — Testes de métricas e painel de uso de IA.
Cobre: resumo de uso, cálculos de percentual/restante, histórico, plano sem IA.
"""
import uuid
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from ia.usage_service import consultar_uso_mensal, LIMITES_MENSAIS


def _session_uso(total=0, tokens_entrada=0, tokens_saida=0, custo=None):
    session = MagicMock()
    row = MagicMock()
    row.total = total
    row.tokens_entrada = tokens_entrada
    row.tokens_saida = tokens_saida
    row.custo_total = custo
    result = MagicMock()
    result.one.return_value = row
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_consultar_uso_sem_registros():
    session = _session_uso(total=0)
    uso = await consultar_uso_mensal(uuid.uuid4(), session)
    assert uso["total_chamadas"] == 0
    assert uso["custo_estimado_usd"] == 0.0
    assert "mes_referencia" in uso


@pytest.mark.asyncio
async def test_consultar_uso_com_registros():
    session = _session_uso(total=15, tokens_entrada=5000, tokens_saida=2000, custo=Decimal("0.002"))
    uso = await consultar_uso_mensal(uuid.uuid4(), session)
    assert uso["total_chamadas"] == 15
    assert uso["tokens_entrada"] == 5000
    assert uso["tokens_saida"] == 2000
    assert uso["custo_estimado_usd"] == pytest.approx(0.002, rel=1e-4)


# ── Cálculos de resumo ───────────────────────────────────────────────────────

def test_calculo_percentual_uso():
    usado = 12
    limite = LIMITES_MENSAIS["PROFISSIONAL"]
    percentual = round(usado / limite * 100, 1)
    assert percentual == 12.0


def test_calculo_restante_profissional():
    usado = 80
    limite = LIMITES_MENSAIS["PROFISSIONAL"]
    restante = max(0, limite - usado)
    assert restante == 20


def test_calculo_restante_nao_negativo():
    usado = 150  # além do limite
    limite = LIMITES_MENSAIS["PROFISSIONAL"]
    restante = max(0, limite - usado)
    assert restante == 0


def test_percentual_cem_quando_limite_atingido():
    usado = 100
    limite = LIMITES_MENSAIS["PROFISSIONAL"]
    percentual = min(round(usado / limite * 100, 1), 100)
    assert percentual == 100.0


def test_enterprise_tem_limite_maior():
    assert LIMITES_MENSAIS["ENTERPRISE"] > LIMITES_MENSAIS["PROFISSIONAL"]


def test_basico_sem_limite():
    assert "BASICO" not in LIMITES_MENSAIS


# ── Plano sem IA ─────────────────────────────────────────────────────────────

def test_ia_disponivel_false_para_basico():
    tier = "BASICO"
    ia_disponivel = LIMITES_MENSAIS.get(tier) is not None
    assert ia_disponivel is False


def test_ia_disponivel_true_para_profissional():
    tier = "PROFISSIONAL"
    ia_disponivel = LIMITES_MENSAIS.get(tier) is not None
    assert ia_disponivel is True


# ── ResumoUsoIA lógica de montagem ───────────────────────────────────────────

def _montar_resumo(tier: str | None, usado: int, custo: float):
    """Simula a lógica do endpoint /ia/uso/resumo."""
    limite = LIMITES_MENSAIS.get(tier or "")
    ia_disponivel = limite is not None
    return {
        "plano": tier,
        "limite_mensal": limite,
        "usado_mes": usado,
        "restante": max(0, limite - usado) if limite is not None else None,
        "percentual_uso": round(usado / limite * 100, 1) if limite else 0.0,
        "custo_estimado_mes": round(custo, 4),
        "ia_disponivel": ia_disponivel,
    }


def test_resumo_profissional_dentro_limite():
    r = _montar_resumo("PROFISSIONAL", 30, 0.009)
    assert r["ia_disponivel"] is True
    assert r["restante"] == 70
    assert r["percentual_uso"] == 30.0


def test_resumo_enterprise():
    r = _montar_resumo("ENTERPRISE", 500, 0.15)
    assert r["limite_mensal"] == 1000
    assert r["restante"] == 500
    assert r["percentual_uso"] == 50.0


def test_resumo_basico_sem_ia():
    r = _montar_resumo("BASICO", 0, 0.0)
    assert r["ia_disponivel"] is False
    assert r["limite_mensal"] is None
    assert r["restante"] is None
    assert r["percentual_uso"] == 0.0


def test_resumo_sem_plano():
    r = _montar_resumo(None, 0, 0.0)
    assert r["ia_disponivel"] is False


def test_resumo_custo_arredondado():
    r = _montar_resumo("PROFISSIONAL", 10, 0.000123456)
    assert r["custo_estimado_mes"] == pytest.approx(0.0001, rel=1e-2)
