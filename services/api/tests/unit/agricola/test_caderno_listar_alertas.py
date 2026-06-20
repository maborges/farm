import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agricola.caderno.service import CadernoCampoService


pytestmark = pytest.mark.asyncio


class FakeRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


async def test_listar_alertas_agrega_ultimos_registros_em_lote():
    tenant_id = uuid.uuid4()
    safra_a = SimpleNamespace(id=uuid.uuid4(), cultura="SOJA", ano_safra="2026/27")
    safra_b = SimpleNamespace(id=uuid.uuid4(), cultura="MILHO", ano_safra="2026/27")
    session = AsyncMock()
    session.execute.side_effect = [
        FakeRowsResult([(safra_a.id, date(2026, 6, 18)), (safra_b.id, date(2026, 5, 20))]),
        FakeRowsResult([(safra_a.id, date(2026, 6, 19))]),
    ]

    svc = CadernoCampoService(session, tenant_id)
    with patch.object(CadernoCampoService, "listar_safras_ativas", AsyncMock(return_value=[safra_a, safra_b])):
        alertas = await svc.listar_alertas(dias_sem_registro=7)

    assert session.execute.await_count == 2
    assert len(alertas) == 1
    assert alertas[0]["safra_id"] == str(safra_b.id)
    assert alertas[0]["dias_desatualizada"] == 31


async def test_listar_alertas_retorna_vazio_quando_nao_houver_safras():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    svc = CadernoCampoService(session, tenant_id)

    with patch.object(CadernoCampoService, "listar_safras_ativas", AsyncMock(return_value=[])):
        alertas = await svc.listar_alertas()

    assert session.execute.await_count == 0
    assert alertas == []
