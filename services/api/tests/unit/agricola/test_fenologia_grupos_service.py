import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agricola.fenologia.grupos_service import SafraTalhaoGrupoService


pytestmark = pytest.mark.asyncio


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


async def test_listar_carrega_itens_em_lote_por_grupo():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    grupo_a = SimpleNamespace(id=uuid.uuid4(), nome="Grupo A", itens=[])
    grupo_b = SimpleNamespace(id=uuid.uuid4(), nome="Grupo B", itens=[])
    item_a1 = SimpleNamespace(id=uuid.uuid4(), grupo_id=grupo_a.id, talhao_id=uuid.uuid4())
    item_a2 = SimpleNamespace(id=uuid.uuid4(), grupo_id=grupo_a.id, talhao_id=uuid.uuid4())
    item_b1 = SimpleNamespace(id=uuid.uuid4(), grupo_id=grupo_b.id, talhao_id=uuid.uuid4())

    session = AsyncMock()
    session.execute.side_effect = [
        FakeScalarResult([grupo_a, grupo_b]),
        FakeScalarResult([item_a1, item_a2, item_b1]),
    ]

    grupos = await SafraTalhaoGrupoService(session, tenant_id).listar(safra_id)

    assert session.execute.await_count == 2
    assert grupos[0].itens == [item_a1, item_a2]
    assert grupos[1].itens == [item_b1]

