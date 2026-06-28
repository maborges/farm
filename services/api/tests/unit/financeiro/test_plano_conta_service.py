import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from financeiro.models.plano_conta import PlanoConta
from financeiro.schemas.plano_conta_schema import PlanoContaCreate
from financeiro.services.plano_conta_service import PlanoContaService


def _mock_execute_first(value):
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = value
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_criar_promove_pai_analitico_para_sintetico_quando_recebe_filho():
    tenant_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    session = _mock_execute_first(None)
    svc = PlanoContaService(session, tenant_id)

    pai = SimpleNamespace(
        id=parent_id,
        natureza="ANALITICA",
        tipo="DESPESA",
        tenant_id=tenant_id,
    )
    svc.get = AsyncMock(return_value=pai)

    payload = PlanoContaCreate(
        parent_id=parent_id,
        codigo="3.99",
        nome="Novo Filho",
        tipo="DESPESA",
        natureza="ANALITICA",
        categoria_rfb="CUSTEIO",
        ordem=99,
    )

    resultado = await svc.criar(payload)

    assert pai.natureza == "SINTETICA"
    assert resultado.parent_id == parent_id
    assert resultado.codigo == "3.99"
    assert resultado.nome == "Novo Filho"
    session.add.assert_called()
    session.flush.assert_awaited()

