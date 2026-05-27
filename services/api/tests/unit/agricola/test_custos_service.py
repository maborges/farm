import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agricola.custos.service import CustosService


def _result(*, scalar_one_or_none=None, scalar_one=None, all_=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalar_one.return_value = scalar_one
    result.all.return_value = all_ or []
    return result


@pytest.mark.asyncio
async def test_resumo_safra_prefere_cost_allocation_com_fonte_oficial():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    safra = SimpleNamespace(id=safra_id, tenant_id=tenant_id, custo_previsto_ha=40.0)
    rows = [
        SimpleNamespace(categoria="INSUMOS", total=200.0),
        SimpleNamespace(categoria="MAO_DE_OBRA", total=300.0),
    ]

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalar_one_or_none=safra),
            _result(scalar_one=10.0),
            _result(scalar_one=0.0),
            _result(all_=rows),
            _result(scalar_one=500.0),
        ]
    )

    service = CustosService(session, tenant_id)
    resumo = await service.get_resumo_safra(safra_id)

    assert resumo.fonte_apuracao == "COST_ALLOCATION"
    assert resumo.usou_fallback_operacional is False
    assert resumo.custo_total_realizado == 500.0
    assert resumo.custo_realizado_por_ha == 50.0
    assert resumo.orcamento_previsto_total == 500.0
    assert resumo.desvio_orcamento_pct == 0.0
    assert len(resumo.breakdown) == 2


@pytest.mark.asyncio
async def test_resumo_safra_explicitamente_explica_fallback_operacional():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    safra = SimpleNamespace(id=safra_id, tenant_id=tenant_id, custo_previsto_ha=None)
    rows = [
        SimpleNamespace(categoria="TRATOR", total=150.0),
        SimpleNamespace(categoria="COLHEITA", total=350.0),
    ]

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalar_one_or_none=safra),
            _result(scalar_one=12.5),
            _result(scalar_one=0.0),
            _result(all_=[]),
            _result(all_=rows),
            _result(scalar_one=0.0),
        ]
    )

    service = CustosService(session, tenant_id)
    resumo = await service.get_resumo_safra(safra_id)

    assert resumo.fonte_apuracao == "OPERACAO_AGRICOLA_FALLBACK"
    assert resumo.usou_fallback_operacional is True
    assert resumo.custo_total_realizado == 500.0
    assert resumo.custo_realizado_por_ha == 40.0
    assert resumo.orcamento_previsto_total is None
    assert resumo.desvio_orcamento_pct is None
    assert len(resumo.breakdown) == 2
