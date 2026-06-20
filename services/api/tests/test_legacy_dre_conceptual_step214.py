"""Step 214 — Testes: separação conceitual entre DRE legada e DRE agrícola v1."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from financeiro.services.relatorio_service import RelatorioService
from financeiro.services.lancamento_service import LancamentoService


@pytest.mark.asyncio
async def test_dre_financeira_simplificada_preserva_saida_e_nao_instancia_dre_agricola_v1():
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(
        all=lambda: [
            SimpleNamespace(categoria_rfb="RECEITA_ATIVIDADE", tipo="RECEITA", total=100.0),
            SimpleNamespace(categoria_rfb="RECEITA_FORA_ATIVIDADE", tipo="RECEITA", total=20.0),
            SimpleNamespace(categoria_rfb="CUSTEIO", tipo="DESPESA", total=70.0),
            SimpleNamespace(categoria_rfb="INVESTIMENTO", tipo="DESPESA", total=15.0),
            SimpleNamespace(categoria_rfb="NAO_DEDUTIVEL", tipo="DESPESA", total=5.0),
        ]
    )

    with (
        patch("agricola.dre.service.DREAgricolaV1Service") as mock_agricola_dre,
    ):
        dre = await RelatorioService(session, tenant_id).dre(
            date(2026, 1, 1),
            date(2026, 1, 31),
            unidade_produtiva_id,
        )

    assert session.execute.await_count == 1
    assert dre.receita_bruta == 100.0
    assert dre.total_custeio == 70.0
    assert dre.total_investimento == 15.0
    assert dre.total_nao_dedutivel == 5.0
    assert dre.resultado_atividade_rural == 30.0
    assert dre.outras_receitas == 20.0
    assert dre.resultado_liquido == 45.0
    assert mock_agricola_dre.call_count == 0


@pytest.mark.asyncio
async def test_dre_operacional_legada_preserva_saida_e_nao_instancia_dre_agricola_v1():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = AsyncMock()
    safra_mock = MagicMock()
    safra_mock.tenant_id = tenant_id
    session.get.return_value = safra_mock

    rec_mock = MagicMock()
    rec_mock.fetchall.return_value = [
        ("VENDA_PRODUCAO", 100000.0),
        ("OUTRAS_RECEITAS", 5000.0),
    ]

    custo_mock = MagicMock()
    custo_mock.fetchall.return_value = [
        ("INSUMOS", 40000.0),
        ("OPERACOES", 20000.0),
        ("MAO_OBRA", 10000.0),
    ]
    session.execute.side_effect = [rec_mock, custo_mock]

    with patch("agricola.dre.service.DREAgricolaV1Service") as mock_agricola_dre:
        dre = await LancamentoService(session, tenant_id).gerar_dre(safra_id)

    assert dre.receita_bruta == 105000.0
    assert dre.custos_operacionais == 70000.0
    assert dre.resultado_operacional == 35000.0
    assert dre.margem_percentual == pytest.approx(33.333, 0.01)
    assert len(dre.breakdown_receitas) == 2
    assert len(dre.breakdown_custos) == 3
    assert mock_agricola_dre.call_count == 0
