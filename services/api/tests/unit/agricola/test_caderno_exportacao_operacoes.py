import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agricola.caderno.service import CadernoExportacaoService


pytestmark = pytest.mark.asyncio


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


async def test_carregar_operacoes_documentais_agrega_por_ids():
    tenant_id = uuid.uuid4()
    op_a = SimpleNamespace(id=uuid.uuid4(), insumos=["a"])
    op_b = SimpleNamespace(id=uuid.uuid4(), insumos=["b"])
    entradas = [
        SimpleNamespace(operacao_id=op_a.id),
        SimpleNamespace(operacao_id=op_b.id),
        SimpleNamespace(operacao_id=op_a.id),
    ]

    session = AsyncMock()
    session.execute.return_value = FakeScalarResult([op_a, op_b])

    svc = CadernoExportacaoService(session, tenant_id)
    operacoes = await svc._carregar_operacoes_documentais(entradas)

    assert session.execute.await_count == 1
    assert operacoes[op_a.id] is op_a
    assert operacoes[op_b.id] is op_b


async def test_carregar_operacoes_documentais_retorna_vazio_sem_ids():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    svc = CadernoExportacaoService(session, tenant_id)

    operacoes = await svc._carregar_operacoes_documentais([])

    assert session.execute.await_count == 0
    assert operacoes == {}

