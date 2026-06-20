import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from financeiro.services.lancamento_service import LancamentoService


pytestmark = pytest.mark.asyncio


async def test_gerar_resumo_inteligente_reusa_contexto_agregado():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = AsyncMock()
    total_mock = MagicMock()
    total_mock.one.return_value = MagicMock(total=1200.0, qtd=3)
    cat_mock = MagicMock()
    cat_mock.first.return_value = ("INSUMOS", 900.0)
    cenario_mock = MagicMock()
    cenario_mock.scalar_one_or_none.return_value = MagicMock(custo_total=1500.0, receita_bruta_total=1000.0)
    serie_mock = MagicMock()
    serie_mock.fetchall.return_value = [("2026-01", 400.0), ("2026-02", 500.0)]
    session.execute.side_effect = [total_mock, cat_mock, cenario_mock, serie_mock]

    resumo = await LancamentoService(session, tenant_id).gerar_resumo_inteligente(safra_id)

    assert session.execute.await_count == 4
    assert "custos registrados" in resumo.resumo
    assert resumo.pontos_atencao
    assert resumo.proximas_acoes


async def test_gerar_alertas_retorna_alerta_de_margem_negativa():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = AsyncMock()
    total_mock = MagicMock()
    total_mock.one.return_value = MagicMock(total=200.0, qtd=1)
    cat_mock = MagicMock()
    cat_mock.first.return_value = ("INSUMOS", 200.0)
    cenario_mock = MagicMock()
    cenario_mock.scalar_one_or_none.return_value = MagicMock(custo_total=2000.0, receita_bruta_total=1500.0)
    serie_mock = MagicMock()
    serie_mock.fetchall.return_value = []
    session.execute.side_effect = [total_mock, cat_mock, cenario_mock, serie_mock]

    alertas = await LancamentoService(session, tenant_id).gerar_alertas(safra_id)

    assert session.execute.await_count == 4
    assert any(alerta.tipo == "MARGEM_NEGATIVA" for alerta in alertas)


async def test_insight_dashboard_reduz_consultas_para_cenario_mais_recente():
    tenant_id = uuid.uuid4()
    session = AsyncMock()

    resumo_mock = MagicMock()
    resumo_mock.one.return_value = MagicMock(total_custos=800.0, quantidade=2)

    safra_mock = MagicMock()
    safra_mock.first.return_value = MagicMock(
        safra_id=uuid.uuid4(),
        ano_safra="2026",
        custo_total=1200.0,
        receita_bruta_total=2000.0,
    )

    cat_mock = MagicMock()
    cat_mock.fetchall.return_value = [("INSUMOS", 500.0)]
    session.execute.side_effect = [resumo_mock, safra_mock, cat_mock]

    insight = await LancamentoService(session, tenant_id).insight_dashboard()

    assert session.execute.await_count == 3
    assert insight.total_custos == 800.0
    assert insight.cenario_margem == 800.0
    assert insight.categorias[0].nome == "INSUMOS"
