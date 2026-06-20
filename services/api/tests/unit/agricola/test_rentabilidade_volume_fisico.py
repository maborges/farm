import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agricola.rentabilidade.service import RentabilidadeAgricolaV1Service


pytestmark = pytest.mark.asyncio


class FakeRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


async def test_calcular_volume_fisico_agrega_consultas_por_lote():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    pu_a = uuid.uuid4()
    pu_b = uuid.uuid4()
    safra_a = uuid.uuid4()
    safra_b = uuid.uuid4()
    area_a = uuid.uuid4()
    area_b = uuid.uuid4()
    session.execute.side_effect = [
        FakeRowsResult(
            [
                SimpleNamespace(id=pu_a, safra_id=safra_a, area_id=area_a),
                SimpleNamespace(id=pu_b, safra_id=safra_b, area_id=area_b),
            ]
        ),
        FakeRowsResult(
            [
                SimpleNamespace(safra_id=safra_a, talhao_id=area_a, total_kg=120.0),
            ]
        ),
        FakeRowsResult(
            [
                SimpleNamespace(safra_id=safra_b, area_id=area_b, produtividade_meta_sc_ha=20.0, area_ha=5.0),
            ]
        ),
    ]

    qtd_sacas, base_volume = await RentabilidadeAgricolaV1Service(session, tenant_id)._calcular_volume_fisico([pu_a, pu_b])

    assert session.execute.await_count == 3
    assert qtd_sacas == pytest.approx((120.0 / 60.0) + (20.0 * 5.0))
    assert base_volume == "REAL"


async def test_calcular_volume_fisico_retorna_indisponivel_sem_pus():
    tenant_id = uuid.uuid4()
    session = AsyncMock()

    qtd_sacas, base_volume = await RentabilidadeAgricolaV1Service(session, tenant_id)._calcular_volume_fisico([])

    assert session.execute.await_count == 0
    assert qtd_sacas == 0.0
    assert base_volume == "INDISPONIVEL"
