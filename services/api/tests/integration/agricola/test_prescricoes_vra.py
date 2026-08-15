from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.prescricoes.schemas import PrescricaoVRACreate
from agricola.prescricoes.service import PrescricaoService
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
)


@pytest.mark.asyncio
async def test_criar_prescricao_persiste_com_schema_alinhado_ao_model(session: AsyncSession):
    """Regressão: schema/model de PrescricaoVRA divergiam da tabela real
    (OPERATIONS-GAP-01, Seção 21.8), fazendo o create quebrar em runtime."""
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    talhao_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)

    dados = PrescricaoVRACreate(
        nome="Reforço N-P-K",
        talhao_id=talhao_id,
        safra_id=safra.id,
        tipo_operacao="ADUBAÇÃO",
        insumo="Ureia Coberta",
        camadas_json=[{"geometry": {}, "rate": 150.0, "unit": "KG/HA"}],
        area_total_ha=15.5,
        quantidade_total_estimada=2500.0,
    )

    svc = PrescricaoService(session, tenant_id)
    criada = await svc.create(dados.model_dump())
    await session.commit()

    assert criada.id is not None
    assert criada.nome == "Reforço N-P-K"
    assert criada.talhao_id == talhao_id
    assert criada.safra_id == safra.id
    assert criada.status == "PENDENTE"

    listadas = await svc.list_all(talhao_id=talhao_id)
    assert len(listadas) == 1
    assert listadas[0].id == criada.id
