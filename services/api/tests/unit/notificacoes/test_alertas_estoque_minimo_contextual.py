from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from notificacoes.alertas_engine import AlertasEngine


@pytest.mark.asyncio
async def test_verificar_estoque_baixo_prioriza_minimo_contextual_do_saldo():
    engine = AlertasEngine()
    session = AsyncMock()

    produto = SimpleNamespace(
        id=uuid4(),
        nome="Produto Contextual",
        unidade_medida="L",
        estoque_minimo=100.0,
    )
    saldo = SimpleNamespace(
        quantidade_atual=45.0,
        estoque_minimo=50.0,
    )
    row = SimpleNamespace(Produto=produto, SaldoEstoque=saldo)

    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    session.execute = AsyncMock(return_value=mock_result)

    alertas = await engine._verificar_estoque_baixo(session, uuid4())

    assert len(alertas) == 1
    alerta = alertas[0]
    assert "45.0/50.0" in alerta.mensagem
    assert alerta.meta["produtos"][0]["estoque_minimo"] == 50.0


@pytest.mark.asyncio
async def test_verificar_estoque_baixo_fallback_catalogo():
    engine = AlertasEngine()
    session = AsyncMock()

    produto = SimpleNamespace(
        id=uuid4(),
        nome="Produto Legado",
        unidade_medida="KG",
        estoque_minimo=80.0,
    )
    saldo = SimpleNamespace(
        quantidade_atual=40.0,
        estoque_minimo=None,
    )
    row = SimpleNamespace(Produto=produto, SaldoEstoque=saldo)

    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    session.execute = AsyncMock(return_value=mock_result)

    alertas = await engine._verificar_estoque_baixo(session, uuid4())

    assert len(alertas) == 1
    alerta = alertas[0]
    assert "40.0/80.0" in alerta.mensagem
    assert alerta.meta["produtos"][0]["estoque_minimo"] == 80.0
