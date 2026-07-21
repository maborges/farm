from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import CultivoArea
from agricola.production_units.models import ProductionUnit
from agricola.production_units.service import ProductionUnitService

pytestmark = pytest.mark.asyncio


def _make_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


def _mock_scalar_one_or_none(value):
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=value)
    return m


def _cultivo_area(*, cultivo_id, area_id, area_ha=10.0) -> CultivoArea:
    return CultivoArea(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        cultivo_id=cultivo_id,
        area_id=area_id,
        area_ha=area_ha,
    )


# ---------------------------------------------------------------------
# 1. sincronizar_de_cultivo_area — criação (nenhuma PU existente)
# ---------------------------------------------------------------------


async def test_sincronizar_cria_pu_com_100_pct_quando_nao_existe():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()
    area_id = uuid.uuid4()

    session = _make_session()
    session.execute.return_value = _mock_scalar_one_or_none(None)
    service = ProductionUnitService(session, tenant_id)

    area = _cultivo_area(cultivo_id=cultivo_id, area_id=area_id, area_ha=12.5)
    pu = await service.sincronizar_de_cultivo_area(area, safra_id=safra_id)

    session.add.assert_called_once()
    assert pu.percentual_participacao == 100.0
    assert pu.status == "ATIVA"
    assert pu.cultivo_area_id == area.id
    assert pu.area_ha == 12.5


# ---------------------------------------------------------------------
# 2. sincronizar_de_cultivo_area — idempotência (PU já existe e ATIVA)
# ---------------------------------------------------------------------


async def test_sincronizar_reaproveita_pu_ativa_existente_sem_duplicar():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()
    area_id = uuid.uuid4()

    pu_existente = ProductionUnit(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        cultivo_area_id=uuid.uuid4(),
        percentual_participacao=60.0,  # ajuste manual de consórcio preexistente
        area_ha=5.0,
        status="ATIVA",
    )

    session = _make_session()
    session.execute.return_value = _mock_scalar_one_or_none(pu_existente)
    service = ProductionUnitService(session, tenant_id)

    nova_area = _cultivo_area(cultivo_id=cultivo_id, area_id=area_id, area_ha=6.0)
    pu = await service.sincronizar_de_cultivo_area(nova_area, safra_id=safra_id)

    session.add.assert_not_called()
    assert pu is pu_existente
    assert pu.cultivo_area_id == nova_area.id
    assert pu.area_ha == 6.0
    # percentual manual preservado — sincronização não sobrescreve
    assert pu.percentual_participacao == 60.0


# ---------------------------------------------------------------------
# 3. sincronizar_de_cultivo_area — reativa PU ENCERRADA em vez de duplicar
# ---------------------------------------------------------------------


async def test_sincronizar_reativa_pu_encerrada_em_vez_de_criar_nova():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()
    area_id = uuid.uuid4()

    pu_encerrada = ProductionUnit(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        cultivo_area_id=None,
        percentual_participacao=100.0,
        area_ha=8.0,
        status="ENCERRADA",
    )

    session = _make_session()
    session.execute.return_value = _mock_scalar_one_or_none(pu_encerrada)
    service = ProductionUnitService(session, tenant_id)

    area = _cultivo_area(cultivo_id=cultivo_id, area_id=area_id, area_ha=8.0)
    pu = await service.sincronizar_de_cultivo_area(area, safra_id=safra_id)

    session.add.assert_not_called()
    assert pu.status == "ATIVA"


# ---------------------------------------------------------------------
# 4. encerrar_por_cultivo_area — encerra, nunca deleta
# ---------------------------------------------------------------------


async def test_encerrar_por_cultivo_area_marca_encerrada_sem_deletar():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()
    area_id = uuid.uuid4()

    pu_ativa = ProductionUnit(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        percentual_participacao=100.0,
        area_ha=4.0,
        status="ATIVA",
    )

    session = _make_session()
    session.execute.return_value = _mock_scalar_one_or_none(pu_ativa)
    service = ProductionUnitService(session, tenant_id)

    await service.encerrar_por_cultivo_area(
        safra_id=safra_id, cultivo_id=cultivo_id, area_id=area_id
    )

    session.delete.assert_not_called()
    assert pu_ativa.status == "ENCERRADA"


async def test_encerrar_por_cultivo_area_silencioso_quando_nao_ha_pu_ativa():
    tenant_id = uuid.uuid4()
    session = _make_session()
    session.execute.return_value = _mock_scalar_one_or_none(None)
    service = ProductionUnitService(session, tenant_id)

    # não deve lançar exceção
    await service.encerrar_por_cultivo_area(
        safra_id=uuid.uuid4(), cultivo_id=uuid.uuid4(), area_id=uuid.uuid4()
    )
    session.delete.assert_not_called()
