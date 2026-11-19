import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

from dateutil.relativedelta import relativedelta
import pytest

from financeiro.services.relatorio_service import RelatorioService


pytestmark = pytest.mark.asyncio


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


async def test_fluxo_caixa_agrega_por_mes_e_calcula_totais():
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = FakeResult(
        [
            SimpleNamespace(
                periodo=date(2026, 1, 1),
                receitas_realizadas=1000.0,
                despesas_realizadas=250.0,
                receitas_previstas=120.0,
                despesas_previstas=40.0,
            ),
            SimpleNamespace(
                periodo=date(2026, 2, 1),
                receitas_realizadas=500.0,
                despesas_realizadas=125.0,
                receitas_previstas=0.0,
                despesas_previstas=60.0,
            ),
        ]
    )

    resposta = await RelatorioService(session, tenant_id).fluxo_caixa(
        date(2026, 1, 1),
        date(2026, 3, 31),
        unidade_produtiva_id,
    )

    assert session.execute.await_count == 1
    assert resposta.unidade_produtiva_id == unidade_produtiva_id
    assert len(resposta.periodos) == 3
    assert resposta.periodos[0].receitas_realizadas == 1000.0
    assert resposta.periodos[0].saldo_realizado == 750.0
    assert resposta.periodos[1].despesas_previstas == 60.0
    assert resposta.periodos[2].saldo_acumulado == 1125.0
    assert resposta.totais.total_receitas_realizadas == 1500.0
    assert resposta.totais.total_despesas_realizadas == 375.0
    assert resposta.totais.total_saldo_realizado == 1125.0


async def test_fluxo_caixa_retorna_zeros_quando_sem_movimentos():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = FakeResult([])

    resposta = await RelatorioService(session, tenant_id).fluxo_caixa(
        date(2026, 4, 1),
        date(2026, 6, 30),
    )

    assert session.execute.await_count == 1
    assert len(resposta.periodos) == 3
    assert all(periodo.receitas_realizadas == 0.0 for periodo in resposta.periodos)
    assert all(periodo.despesas_realizadas == 0.0 for periodo in resposta.periodos)
    assert resposta.totais.total_saldo_previsto == 0.0
    assert resposta.analise_decisao_reativa is not None
    assert resposta.analise_decisao_reativa.possui_vale_caixa is False
    assert resposta.analise_decisao_reativa.nivel_risco == "SAUDAVEL"


async def test_fluxo_caixa_detecta_vale_capital_giro_e_calcula_custo_decisao_reativa():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    inicio = date.today().replace(day=1) + relativedelta(months=2)
    mes2 = inicio + relativedelta(months=1)
    fim = (inicio + relativedelta(months=2, day=31))

    session.execute.return_value = FakeResult(
        [
            SimpleNamespace(
                periodo=inicio,
                receitas_realizadas=0.0,
                despesas_realizadas=0.0,
                receitas_previstas=20_000.0,
                despesas_previstas=120_000.0,
            ),
            SimpleNamespace(
                periodo=mes2,
                receitas_realizadas=0.0,
                despesas_realizadas=0.0,
                receitas_previstas=0.0,
                despesas_previstas=50_000.0,
            ),
        ]
    )

    resposta = await RelatorioService(session, tenant_id).fluxo_caixa(
        inicio,
        fim,
        saldo_inicial=0.0,
        taxa_credito_planejado_aa=8.5,
        taxa_credito_reativo_aa=24.0,
    )

    assert session.execute.await_count == 1
    assert resposta.periodos[0].em_vale_caixa is True
    assert resposta.periodos[0].saldo_acumulado_projetado == -100_000.0
    assert resposta.periodos[1].saldo_acumulado_projetado == -150_000.0
    assert resposta.periodos[2].saldo_acumulado_projetado == -150_000.0

    analise = resposta.analise_decisao_reativa
    assert analise is not None
    assert analise.possui_vale_caixa is True
    assert analise.meses_em_deficit == 3
    assert analise.pior_vale_valor == 150_000.0
    assert analise.mes_pior_vale == mes2
    assert analise.primeiro_mes_vale == inicio
    assert analise.custo_juros_reativo > analise.custo_juros_planejado
    assert analise.custo_decisao_reativa > 0


async def test_fluxo_caixa_com_saldo_inicial_absorve_vale_e_fica_saudavel():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    inicio = date.today().replace(day=1) + relativedelta(months=2)
    fim = (inicio + relativedelta(months=1, day=31))

    session.execute.return_value = FakeResult(
        [
            SimpleNamespace(
                periodo=inicio,
                receitas_realizadas=0.0,
                despesas_realizadas=0.0,
                receitas_previstas=50_000.0,
                despesas_previstas=150_000.0,
            ),
        ]
    )

    resposta = await RelatorioService(session, tenant_id).fluxo_caixa(
        inicio,
        fim,
        saldo_inicial=120_000.0,
    )

    assert resposta.periodos[0].saldo_acumulado_projetado == 20_000.0
    assert resposta.periodos[0].em_vale_caixa is False
    analise = resposta.analise_decisao_reativa
    assert analise is not None
    assert analise.possui_vale_caixa is False
    assert analise.nivel_risco == "SAUDAVEL"
    assert analise.custo_decisao_reativa == 0.0


async def test_fluxo_caixa_classifica_alerta_vs_critico_por_antecedencia():
    tenant_id = uuid.uuid4()
    session_critico = AsyncMock()
    mes_corrente = date.today().replace(day=1)

    session_critico.execute.return_value = FakeResult(
        [
            SimpleNamespace(
                periodo=mes_corrente,
                receitas_realizadas=0.0,
                despesas_realizadas=0.0,
                receitas_previstas=0.0,
                despesas_previstas=80_000.0,
            ),
        ]
    )
    res_critico = await RelatorioService(session_critico, tenant_id).fluxo_caixa(
        mes_corrente,
        mes_corrente + relativedelta(day=31),
    )
    assert res_critico.analise_decisao_reativa is not None
    assert res_critico.analise_decisao_reativa.nivel_risco == "CRITICO"

    session_alerta = AsyncMock()
    mes_futuro = mes_corrente + relativedelta(months=3)
    session_alerta.execute.return_value = FakeResult(
        [
            SimpleNamespace(
                periodo=mes_futuro,
                receitas_realizadas=0.0,
                despesas_realizadas=0.0,
                receitas_previstas=0.0,
                despesas_previstas=80_000.0,
            ),
        ]
    )
    res_alerta = await RelatorioService(session_alerta, tenant_id).fluxo_caixa(
        mes_futuro,
        mes_futuro + relativedelta(day=31),
    )
    assert res_alerta.analise_decisao_reativa is not None
    assert res_alerta.analise_decisao_reativa.nivel_risco == "ALERTA"
