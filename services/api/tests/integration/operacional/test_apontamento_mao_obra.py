from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from core.exceptions import BusinessRuleError
from operacional.models.apontamento import ApontamentoMaoObra
from operacional.schemas.apontamento import ApontamentoMaoObraCreate
from operacional.services.apontamento_mao_obra_service import ApontamentoMaoObraService
from rh.models import ColaboradorRH
from test_frota_apontamentos_step08 import (
    _criar_area,
    _criar_cultivo,
    _criar_operador,
    _criar_production_unit,
    _criar_safra,
    _criar_up,
    _garantir_tenant,
)


@pytest.mark.asyncio
async def test_apontamento_mao_obra_calcula_custo_via_colaborador_e_gera_cost_allocation(session: AsyncSession):
    """OPERATIONS-GAP-01 §21.14: elo estruturado entre execução manual e
    CostAllocation, mesmo papel que FrotaApontamentoService cumpre para máquinas."""
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "Fazenda Teste")
    area_id = await _criar_area(session, tenant_id, up_id, "Talhão 1")
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    pessoa = await _criar_operador(session, tenant_id, up_id, "Trabalhador Rural")

    colaborador = ColaboradorRH(
        tenant_id=tenant_id, pessoa_id=pessoa.id, tipo_contrato="DIARISTA",
        valor_hora=20.0, ativo=True,
    )
    session.add(colaborador)
    await session.commit()

    svc = ApontamentoMaoObraService(session, tenant_id)
    apontamento = await svc.criar(ApontamentoMaoObraCreate(
        pessoa_id=pessoa.id,
        data=datetime.now(timezone.utc),
        horas_trabalhadas=8.0,
        quantidade_pessoas=3,
        safra_id=safra.id,
        talhao_id=area_id,
        tipo_operacao="CAPINA_MANUAL",
    ))
    await session.commit()

    assert apontamento.production_unit_id == pu.id
    assert apontamento.custo_hora_snapshot == pytest.approx(20.0)
    # 20/h * 8h * 3 pessoas = 480
    assert apontamento.custo_total == pytest.approx(480.0)

    allocation = (await session.execute(
        select(CostAllocation).where(
            CostAllocation.tenant_id == tenant_id,
            CostAllocation.source == "APONTAMENTO_MAO_OBRA",
            CostAllocation.source_id == apontamento.id,
        )
    )).scalar_one_or_none()
    assert allocation is not None
    assert allocation.cost_category == "MAO_OBRA"
    assert float(allocation.amount) == pytest.approx(480.0)


@pytest.mark.asyncio
async def test_apontamento_mao_obra_sem_colaborador_fica_sem_custo(session: AsyncSession):
    """Sem ColaboradorRH e sem custo_hora_snapshot manual, não inventa valor
    (mesma disciplina defensiva do PlanoOperacional)."""
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "Fazenda Teste")
    pessoa = await _criar_operador(session, tenant_id, up_id, "Trabalhador Sem Cadastro RH")

    svc = ApontamentoMaoObraService(session, tenant_id)
    apontamento = await svc.criar(ApontamentoMaoObraCreate(
        pessoa_id=pessoa.id,
        data=datetime.now(timezone.utc),
        horas_trabalhadas=6.0,
    ))
    await session.commit()

    assert apontamento.custo_hora_snapshot is None
    assert apontamento.custo_total is None
