from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select

from agricola.custos.models import CostAllocation
from agricola.production_units.models import ProductionUnit
from core.cadastros.produtos.models import Produto
from operacional.models.estoque import Deposito, SaldoEstoque
from operacional.schemas.estoque import AjusteEstoqueRequest
from operacional.services.estoque_service import EstoqueService
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_cultivo,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
)


async def _criar_deposito(session, tenant_id, unidade_produtiva_id) -> uuid.UUID:
    deposito = Deposito(tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id, nome="Depósito Perda Teste")
    session.add(deposito)
    await session.commit()
    await session.refresh(deposito)
    return deposito.id


async def _criar_produto(session, tenant_id) -> uuid.UUID:
    produto = Produto(tenant_id=tenant_id, nome="Fertilizante Teste", tipo="FERTILIZANTE", unidade_medida="KG")
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto.id


async def _criar_saldo(session, deposito_id, produto_id, *, quantidade: float, custo_medio: float) -> None:
    saldo = SaldoEstoque(deposito_id=deposito_id, produto_id=produto_id, quantidade_atual=quantidade, custo_medio=custo_medio)
    session.add(saldo)
    await session.commit()


async def _criar_production_unit(session, tenant_id, safra_id, cultivo_id, area_id) -> uuid.UUID:
    pu = ProductionUnit(
        tenant_id=tenant_id, safra_id=safra_id, cultivo_id=cultivo_id, area_id=area_id,
        percentual_participacao=100.0, area_ha=10.0, status="ATIVA",
    )
    session.add(pu)
    await session.commit()
    await session.refresh(pu)
    return pu.id


async def _setup_base(session, tenant_id):
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    deposito_id = await _criar_deposito(session, tenant_id, unidade_id)
    produto_id = await _criar_produto(session, tenant_id)
    return unidade_id, area_id, safra.id, cultivo_id, deposito_id, produto_id


@pytest.mark.asyncio
async def test_perda_com_pu_resolvivel_gera_cost_allocation(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, area_id, safra_id, cultivo_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    await _criar_production_unit(session, tenant_id, safra_id, cultivo_id, area_id)
    await _criar_saldo(session, deposito_id, produto_id, quantidade=100.0, custo_medio=10.0)

    svc = EstoqueService(session, tenant_id)
    mov = await svc.registrar_ajuste(AjusteEstoqueRequest(
        deposito_id=deposito_id, produto_id=produto_id, quantidade_nova=90.0,
        motivo="Fertilizante estragado", categoria_ajuste="PERDA",
        safra_id=safra_id, talhao_id=area_id,
    ))
    await session.commit()

    stmt = select(CostAllocation).where(
        CostAllocation.tenant_id == tenant_id,
        CostAllocation.inventory_movement_id == mov.id,
    )
    allocation = (await session.execute(stmt)).scalars().first()
    assert allocation is not None
    assert allocation.source == "PERDA_ESTOQUE"
    assert allocation.cost_category == "OUTROS"
    assert float(allocation.amount) == 100.0  # 10 kg perdidos * custo_medio 10.0


@pytest.mark.asyncio
async def test_perda_sem_safra_talhao_nao_gera_custo(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, area_id, safra_id, cultivo_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    await _criar_production_unit(session, tenant_id, safra_id, cultivo_id, area_id)
    await _criar_saldo(session, deposito_id, produto_id, quantidade=100.0, custo_medio=10.0)

    svc = EstoqueService(session, tenant_id)
    mov = await svc.registrar_ajuste(AjusteEstoqueRequest(
        deposito_id=deposito_id, produto_id=produto_id, quantidade_nova=90.0,
        motivo="Perda sem vínculo", categoria_ajuste="PERDA",
    ))
    await session.commit()

    stmt = select(CostAllocation).where(CostAllocation.inventory_movement_id == mov.id)
    assert (await session.execute(stmt)).scalars().first() is None


@pytest.mark.asyncio
async def test_contagem_inventario_nunca_gera_custo(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, area_id, safra_id, cultivo_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    await _criar_production_unit(session, tenant_id, safra_id, cultivo_id, area_id)
    await _criar_saldo(session, deposito_id, produto_id, quantidade=100.0, custo_medio=10.0)

    svc = EstoqueService(session, tenant_id)
    mov = await svc.registrar_ajuste(AjusteEstoqueRequest(
        deposito_id=deposito_id, produto_id=produto_id, quantidade_nova=90.0,
        motivo="Correção de contagem", categoria_ajuste="CONTAGEM_INVENTARIO",
        safra_id=safra_id, talhao_id=area_id,
    ))
    await session.commit()

    stmt = select(CostAllocation).where(CostAllocation.inventory_movement_id == mov.id)
    assert (await session.execute(stmt)).scalars().first() is None


@pytest.mark.asyncio
async def test_perda_com_pu_nao_resolvivel_nao_gera_custo(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, area_id, safra_id, cultivo_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    # Nenhum ProductionUnit criado para esse par safra+talhão.
    await _criar_saldo(session, deposito_id, produto_id, quantidade=100.0, custo_medio=10.0)

    svc = EstoqueService(session, tenant_id)
    mov = await svc.registrar_ajuste(AjusteEstoqueRequest(
        deposito_id=deposito_id, produto_id=produto_id, quantidade_nova=90.0,
        motivo="Perda sem PU cadastrado", categoria_ajuste="PERDA",
        safra_id=safra_id, talhao_id=area_id,
    ))
    await session.commit()

    stmt = select(CostAllocation).where(CostAllocation.inventory_movement_id == mov.id)
    assert (await session.execute(stmt)).scalars().first() is None


@pytest.mark.asyncio
async def test_isolamento_tenant_perda(session_a, session_b, tenant_id, outro_tenant_id):
    await _garantir_tenant(session_a, tenant_id)
    unidade_id, area_id, safra_id, cultivo_id, deposito_id, produto_id = await _setup_base(session_a, tenant_id)
    await _criar_production_unit(session_a, tenant_id, safra_id, cultivo_id, area_id)
    await _criar_saldo(session_a, deposito_id, produto_id, quantidade=100.0, custo_medio=10.0)

    svc_a = EstoqueService(session_a, tenant_id)
    mov = await svc_a.registrar_ajuste(AjusteEstoqueRequest(
        deposito_id=deposito_id, produto_id=produto_id, quantidade_nova=90.0,
        motivo="Perda tenant A", categoria_ajuste="PERDA",
        safra_id=safra_id, talhao_id=area_id,
    ))
    await session_a.commit()

    stmt = select(CostAllocation).where(
        CostAllocation.tenant_id == outro_tenant_id,
        CostAllocation.inventory_movement_id == mov.id,
    )
    assert (await session_b.execute(stmt)).scalars().first() is None
