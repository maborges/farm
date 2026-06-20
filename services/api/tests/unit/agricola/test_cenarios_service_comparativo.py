import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agricola.cenarios.service import CenariosService
from core.exceptions import EntityNotFoundError


pytestmark = pytest.mark.asyncio


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


async def test_get_comparativo_carrega_cenarios_em_lote():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    c1 = SimpleNamespace(
        id=uuid.uuid4(),
        nome="Base",
        tipo="BASE",
        eh_base=True,
        area_total_ha=10.0,
        receita_bruta_total=1000.0,
        custo_total=500.0,
        margem_contribuicao_total=500.0,
        depreciacao_total=0.0,
        ir_aliquota_pct=0.0,
        ir_valor_total=0.0,
        resultado_liquido_total=500.0,
        ponto_equilibrio_sc_ha=1.0,
        unidades=[],
    )
    c2 = SimpleNamespace(
        id=uuid.uuid4(),
        nome="Otimista",
        tipo="OTIMISTA",
        eh_base=False,
        area_total_ha=10.0,
        receita_bruta_total=1200.0,
        custo_total=400.0,
        margem_contribuicao_total=800.0,
        depreciacao_total=0.0,
        ir_aliquota_pct=0.0,
        ir_valor_total=0.0,
        resultado_liquido_total=800.0,
        ponto_equilibrio_sc_ha=0.8,
        unidades=[],
    )
    session = AsyncMock()
    session.execute.return_value = FakeScalarResult([c1, c2])

    resposta = await CenariosService(session, tenant_id).get_comparativo(safra_id, [c1.id, c2.id])

    assert session.execute.await_count == 1
    assert [c.cenario_id for c in resposta.cenarios] == [c1.id, c2.id]


async def test_get_comparativo_falha_quando_cenario_nao_existe():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    c1 = SimpleNamespace(
        id=uuid.uuid4(),
        nome="Base",
        tipo="BASE",
        eh_base=True,
        area_total_ha=10.0,
        receita_bruta_total=1000.0,
        custo_total=500.0,
        margem_contribuicao_total=500.0,
        depreciacao_total=0.0,
        ir_aliquota_pct=0.0,
        ir_valor_total=0.0,
        resultado_liquido_total=500.0,
        ponto_equilibrio_sc_ha=1.0,
        unidades=[],
    )
    session = AsyncMock()
    session.execute.return_value = FakeScalarResult([c1])

    with pytest.raises(EntityNotFoundError):
        await CenariosService(session, tenant_id).get_comparativo(safra_id, [c1.id, uuid.uuid4()])

