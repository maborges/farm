from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agricola.cultivos.schemas import CultivoAreaCreate
from agricola.cultivos.service import CultivoService

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_validar_ocupacao_talhao_agrega_consultas_por_lote():
    session = AsyncMock()
    tenant_id = uuid4()
    svc = CultivoService(session, tenant_id)

    area_1 = uuid4()
    area_2 = uuid4()
    talhao_1 = SimpleNamespace(id=area_1, nome="Talhão 1", area_hectares=10.0)
    talhao_2 = SimpleNamespace(id=area_2, nome="Talhão 2", area_hectares=12.0)
    cultivo_1 = SimpleNamespace(id=uuid4(), consorciado=False, data_inicio=None, data_fim=None)
    cultivo_2 = SimpleNamespace(id=uuid4(), consorciado=False, data_inicio=None, data_fim=None)

    result_talhoes = MagicMock()
    result_talhoes.scalars.return_value.all.return_value = [talhao_1, talhao_2]
    result_cultivos = MagicMock()
    result_cultivos.all.return_value = [
        (area_1, cultivo_1),
        (area_2, cultivo_2),
    ]
    result_areas = MagicMock()
    result_areas.all.return_value = [
        (area_1, cultivo_1.id, 5.0),
        (area_2, cultivo_2.id, 2.0),
    ]
    session.execute.side_effect = [result_talhoes, result_cultivos, result_areas]

    await svc._validar_ocupacao_talhao(
        safra_id=uuid4(),
        areas_data=[
            CultivoAreaCreate(area_id=area_1, area_ha=3.0),
            CultivoAreaCreate(area_id=area_2, area_ha=4.0),
        ],
        consorciado=False,
        data_inicio=date(2025, 1, 1),
        data_fim=date(2025, 12, 31),
    )

    assert session.execute.await_count == 3
