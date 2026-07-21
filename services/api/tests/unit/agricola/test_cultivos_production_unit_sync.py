from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agricola.cultivos.schemas import CultivoAreaCreate, CultivoCreate
from agricola.cultivos.service import CultivoService
from agricola.production_units.service import ProductionUnitService

pytestmark = pytest.mark.asyncio


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------
# 1. criar_com_areas sincroniza PU para cada área criada
# ---------------------------------------------------------------------


async def test_criar_com_areas_sincroniza_pu_para_cada_area():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    area_id = uuid.uuid4()

    session = _make_session()
    svc = CultivoService(session, tenant_id)
    svc._get_safra = AsyncMock(return_value=SimpleNamespace(id=safra_id))
    svc._validar_ocupacao_talhao = AsyncMock(return_value=None)

    dados = CultivoCreate(
        cultura="SOJA",
        areas=[CultivoAreaCreate(area_id=area_id, area_ha=10.0)],
    )

    with patch.object(
        ProductionUnitService, "sincronizar_de_cultivo_area", new=AsyncMock()
    ) as sync_mock:
        await svc.criar_com_areas(safra_id, dados)

    sync_mock.assert_awaited_once()
    _, kwargs = sync_mock.await_args
    assert kwargs["safra_id"] == safra_id
    area_arg = sync_mock.await_args.args[0]
    assert area_arg.area_id == area_id


# ---------------------------------------------------------------------
# 2. sincronizar_areas encerra PU das áreas removidas e sincroniza as mantidas/novas
# ---------------------------------------------------------------------


async def test_sincronizar_areas_encerra_removidas_e_sincroniza_atuais():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()
    area_removida_id = uuid.uuid4()
    area_mantida_id = uuid.uuid4()

    session = _make_session()
    svc = CultivoService(session, tenant_id)

    cultivo = SimpleNamespace(
        id=cultivo_id, safra_id=safra_id, consorciado=False, data_inicio=None, data_fim=None
    )
    svc.get_or_fail = AsyncMock(return_value=cultivo)
    svc._validar_ocupacao_talhao = AsyncMock(return_value=None)

    area_removida = SimpleNamespace(id=uuid.uuid4(), area_id=area_removida_id)
    area_mantida = SimpleNamespace(id=uuid.uuid4(), area_id=area_mantida_id)
    old_areas_result = MagicMock()
    old_areas_result.scalars.return_value.all.return_value = [area_removida, area_mantida]
    session.execute.return_value = old_areas_result

    novas_areas_data = [CultivoAreaCreate(area_id=area_mantida_id, area_ha=7.0)]

    with patch.object(
        ProductionUnitService, "encerrar_por_cultivo_area", new=AsyncMock()
    ) as encerrar_mock, patch.object(
        ProductionUnitService, "sincronizar_de_cultivo_area", new=AsyncMock()
    ) as sync_mock:
        await svc.sincronizar_areas(cultivo_id, novas_areas_data)

    encerrar_mock.assert_awaited_once()
    _, encerrar_kwargs = encerrar_mock.await_args
    assert encerrar_kwargs["area_id"] == area_removida_id
    assert encerrar_kwargs["safra_id"] == safra_id
    assert encerrar_kwargs["cultivo_id"] == cultivo_id

    sync_mock.assert_awaited_once()
    sync_area_arg = sync_mock.await_args.args[0]
    assert sync_area_arg.area_id == area_mantida_id
