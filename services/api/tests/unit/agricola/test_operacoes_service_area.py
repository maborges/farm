import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agricola.operacoes.service import OperacaoService
from core.exceptions import BusinessRuleError


@pytest.mark.asyncio
async def test_validar_area_aplicada_rejeita_quando_maior_que_area_do_talhao():
    session = AsyncMock()
    session.get = AsyncMock(
        return_value=SimpleNamespace(
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            area_hectares=Decimal("10.0"),
            area_hectares_manual=None,
        )
    )
    service = OperacaoService(
        session=session,
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )

    with pytest.raises(BusinessRuleError, match="não pode ser maior que a área do talhão"):
        await service._validar_area_aplicada(uuid.uuid4(), 12.0)


@pytest.mark.asyncio
async def test_validar_area_aplicada_rejeita_talhao_sem_area_cadastrada():
    session = AsyncMock()
    session.get = AsyncMock(
        return_value=SimpleNamespace(
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            area_hectares=None,
            area_hectares_manual=None,
        )
    )
    service = OperacaoService(
        session=session,
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )

    with pytest.raises(BusinessRuleError, match="não possui área calculada ou informada"):
        await service._validar_area_aplicada(uuid.uuid4(), 5.0)


@pytest.mark.asyncio
async def test_validar_area_aplicada_aceita_area_manual_do_talhao():
    session = AsyncMock()
    session.get = AsyncMock(
        return_value=SimpleNamespace(
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            area_hectares=None,
            area_hectares_manual=Decimal("8.5"),
        )
    )
    service = OperacaoService(
        session=session,
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )

    area = await service._validar_area_aplicada(uuid.uuid4(), 8.5)

    assert area == 8.5
