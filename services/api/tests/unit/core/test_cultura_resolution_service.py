from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.services.cultura_resolution_service import (
    CulturaResolutionService,
    CulturaResolutionSource,
    CulturaResolutionStatus,
)

TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


def _make_session() -> MagicMock:
    session = MagicMock()
    session.execute = AsyncMock()
    return session


def _result_scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _result_scalars(values):
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


@pytest.mark.asyncio
async def test_resolve_by_cultivo_prioriza_cultivar_id():
    session = _make_session()
    cultivo_id = uuid.uuid4()
    cultura_id = uuid.uuid4()
    cultivo = SimpleNamespace(
        id=cultivo_id,
        safra_id=uuid.uuid4(),
        cultivar_id=cultura_id,
        cultura="SOJA",
    )
    cultura = SimpleNamespace(id=cultura_id, nome="Soja", nome_cientifico="Glycine max")
    session.execute.side_effect = [_result_scalar(cultivo), _result_scalar(cultura)]

    service = CulturaResolutionService(session, TENANT_ID)
    result = await service.resolve_by_cultivo(cultivo_id)

    assert result.status == CulturaResolutionStatus.RESOLVED
    assert result.source == CulturaResolutionSource.CULTIVAR_ID
    assert result.cultura_id == cultura_id
    assert result.nome == "Soja"


@pytest.mark.asyncio
async def test_resolve_by_cultivo_fallback_para_texto():
    session = _make_session()
    cultivo_id = uuid.uuid4()
    cultivo = SimpleNamespace(
        id=cultivo_id,
        safra_id=uuid.uuid4(),
        cultivar_id=None,
        cultura="SOJA",
    )
    cultura = SimpleNamespace(id=uuid.uuid4(), nome="SOJA", nome_cientifico=None)
    session.execute.side_effect = [_result_scalar(cultivo), _result_scalar(cultura)]

    service = CulturaResolutionService(session, TENANT_ID)
    result = await service.resolve_by_cultivo(cultivo_id)

    assert result.status == CulturaResolutionStatus.RESOLVED
    assert result.source == CulturaResolutionSource.CULTIVO_TEXTO
    assert result.matched_text == "SOJA"
    assert result.nome == "SOJA"


@pytest.mark.asyncio
async def test_resolve_by_safra_fallback_para_texto_da_safra():
    session = _make_session()
    safra_id = uuid.uuid4()
    safra = SimpleNamespace(id=safra_id, tenant_id=TENANT_ID, cultura="MILHO")
    cultura = SimpleNamespace(id=uuid.uuid4(), nome="MILHO", nome_cientifico=None)
    session.execute.side_effect = [
        _result_scalars([]),
        _result_scalar(safra),
        _result_scalar(cultura),
    ]

    service = CulturaResolutionService(session, TENANT_ID)
    result = await service.resolve_by_safra(safra_id)

    assert result.status == CulturaResolutionStatus.RESOLVED
    assert result.source == CulturaResolutionSource.SAFRA_TEXTO
    assert result.matched_text == "MILHO"


@pytest.mark.asyncio
async def test_resolve_by_safra_retorna_not_found_quando_nada_existe():
    session = _make_session()
    safra_id = uuid.uuid4()
    safra = SimpleNamespace(id=safra_id, tenant_id=TENANT_ID, cultura=None)
    session.execute.side_effect = [_result_scalars([]), _result_scalar(safra)]

    service = CulturaResolutionService(session, TENANT_ID)
    result = await service.resolve_by_safra(safra_id)

    assert result.status == CulturaResolutionStatus.NOT_FOUND
    assert result.source == CulturaResolutionSource.NOT_FOUND
    assert result.safra_id == safra_id


@pytest.mark.asyncio
async def test_resolve_by_safra_preserva_compatibilidade_com_dado_antigo():
    session = _make_session()
    safra_id = uuid.uuid4()
    cultivo = SimpleNamespace(
        id=uuid.uuid4(),
        safra_id=safra_id,
        cultivar_id=None,
        cultura="SEM_MAPEAMENTO",
    )
    safra = SimpleNamespace(id=safra_id, tenant_id=TENANT_ID, cultura="TRIGO")
    cultura = SimpleNamespace(id=uuid.uuid4(), nome="TRIGO", nome_cientifico=None)
    session.execute.side_effect = [
        _result_scalars([cultivo]),
        _result_scalar(None),
        _result_scalar(safra),
        _result_scalar(cultura),
    ]

    service = CulturaResolutionService(session, TENANT_ID)
    result = await service.resolve_by_safra(safra_id)

    assert result.status == CulturaResolutionStatus.RESOLVED
    assert result.source == CulturaResolutionSource.SAFRA_TEXTO
    assert result.nome == "TRIGO"
