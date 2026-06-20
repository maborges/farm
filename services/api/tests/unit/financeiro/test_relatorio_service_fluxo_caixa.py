import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

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
