"""Step 122 — Testes: precificação e margem dos créditos de IA"""
import pytest
from decimal import Decimal
from fastapi import HTTPException

from ia.router import (
    _calcular_valor,
    _calcular_margem,
    _validar_margem,
    CUSTO_ESTIMADO_CREDITO_IA,
    MARGEM_MINIMA_IA_PERCENTUAL,
)


# ── _calcular_valor ───────────────────────────────────────────────────────────

def test_calcular_valor_faixa_minima():
    assert _calcular_valor(10) == Decimal("1.00")


def test_calcular_valor_faixa_200():
    # R$ 0.09 × 200 = R$ 18.00
    assert _calcular_valor(200) == Decimal("18.00")


def test_calcular_valor_faixa_500():
    assert _calcular_valor(500) == Decimal("40.00")


def test_calcular_valor_faixa_1000():
    assert _calcular_valor(1000) == Decimal("70.00")


# ── _calcular_margem ──────────────────────────────────────────────────────────

def test_calcular_margem_100_creditos():
    valor = _calcular_valor(100)  # R$ 10.00
    resultado = _calcular_margem(valor, 100)

    custo_esperado = (CUSTO_ESTIMADO_CREDITO_IA * 100).quantize(Decimal("0.01"))
    margem_esperada = (valor - custo_esperado).quantize(Decimal("0.01"))
    pct_esperado = ((margem_esperada / valor) * 100).quantize(Decimal("0.01"))

    assert resultado["custo_estimado"] == custo_esperado
    assert resultado["margem_estimada"] == margem_esperada
    assert resultado["margem_percentual"] == pct_esperado


def test_calcular_margem_positiva():
    """Margem deve ser positiva para preços padrão."""
    for qtd in [100, 200, 500, 1000]:
        valor = _calcular_valor(qtd)
        info = _calcular_margem(valor, qtd)
        assert info["margem_estimada"] > 0
        assert info["margem_percentual"] > 0


def test_calcular_margem_detalhes_salvos():
    """Resultado contém todas as chaves esperadas."""
    valor = _calcular_valor(100)
    info = _calcular_margem(valor, 100)
    assert "custo_estimado" in info
    assert "margem_estimada" in info
    assert "margem_percentual" in info


# ── _validar_margem ───────────────────────────────────────────────────────────

def test_validar_margem_suficiente_passa():
    """Margem acima do mínimo não levanta exceção."""
    _validar_margem(MARGEM_MINIMA_IA_PERCENTUAL + Decimal("10"))


def test_validar_margem_exatamente_minima_passa():
    _validar_margem(MARGEM_MINIMA_IA_PERCENTUAL)


def test_validar_margem_insuficiente_bloqueia():
    """Margem abaixo do mínimo deve bloquear com 422."""
    with pytest.raises(HTTPException) as exc:
        _validar_margem(MARGEM_MINIMA_IA_PERCENTUAL - Decimal("1"))
    assert exc.value.status_code == 422


def test_validar_margem_zero_bloqueia():
    with pytest.raises(HTTPException) as exc:
        _validar_margem(Decimal("0"))
    assert exc.value.status_code == 422


# ── integração: preços padrão passam na validação ─────────────────────────────

def test_precos_padrao_passam_margem():
    """Todos os preços padrão devem ter margem suficiente."""
    for qtd in [100, 200, 500, 1000]:
        valor = _calcular_valor(qtd)
        info = _calcular_margem(valor, qtd)
        # não deve levantar
        _validar_margem(info["margem_percentual"])
