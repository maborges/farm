from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.custos.service import calcular_custo_unitario_snapshot
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.production_units.models import ProductionUnit
from test_operational_workflow_governance_step02 import _garantir_unidade_ha
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_cultivo,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
)


async def _criar_production_unit(session, tenant_id, safra_id, cultivo_id, area_id, percentual: float = 100.0) -> ProductionUnit:
    pu = ProductionUnit(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        percentual_participacao=percentual,
        area_ha=10.0,
        status="ATIVA",
    )
    session.add(pu)
    await session.commit()
    await session.refresh(pu)
    return pu


async def _registrar_custo_operacao(session, *, tenant_id, safra_id, cultivo_id, area_id, pu_id, unidade_ha_id, valor, data):
    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        production_unit_id=pu_id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação com custo para snapshot",
        data_realizada=data,
        custo_total=valor,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.flush()
    execucao = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao.id,
        production_unit_id=pu_id,
        data_execucao=data,
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id,
        custo_real=valor,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add(execucao)
    await session.flush()
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu_id,
        source="OPERATION_EXECUTION",
        source_id=execucao.id,
        operation_execution_id=execucao.id,
        amount=valor,
        allocation_date=data,
        cost_category="OUTROS",
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )
    await session.commit()


@pytest.mark.asyncio
async def test_snapshot_calcula_custo_unitario_com_pu_unico(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    unidade_ha_id = await _garantir_unidade_ha(session, tenant_id)

    hoje = date.today()
    await _registrar_custo_operacao(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        pu_id=pu.id,
        unidade_ha_id=unidade_ha_id,
        valor=1000.0,
        data=hoje,
    )

    resultado = await calcular_custo_unitario_snapshot(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        talhao_id=area_id,
        quantidade_lote=100.0,
        data_referencia=hoje,
    )

    assert resultado == 10.0


@pytest.mark.asyncio
async def test_snapshot_retorna_none_quando_pu_ambiguo(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    # Duas ProductionUnits para o mesmo par safra+talhão (ex. consórcio 50/50).
    await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id, percentual=50.0)
    await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id, percentual=50.0)

    resultado = await calcular_custo_unitario_snapshot(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        talhao_id=area_id,
        quantidade_lote=50.0,
        data_referencia=date.today(),
    )

    assert resultado is None


@pytest.mark.asyncio
async def test_snapshot_retorna_none_quando_pu_inexistente(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)

    resultado = await calcular_custo_unitario_snapshot(
        session,
        tenant_id=tenant_id,
        safra_id=uuid.uuid4(),
        talhao_id=uuid.uuid4(),
        quantidade_lote=50.0,
        data_referencia=date.today(),
    )

    assert resultado is None


@pytest.mark.asyncio
async def test_snapshot_ignora_custo_lancado_apos_data_referencia(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    unidade_ha_id = await _garantir_unidade_ha(session, tenant_id)

    data_colheita = date(2026, 1, 10)
    data_custo_futuro = date(2026, 1, 20)
    await _registrar_custo_operacao(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        pu_id=pu.id,
        unidade_ha_id=unidade_ha_id,
        valor=500.0,
        data=data_custo_futuro,
    )

    resultado = await calcular_custo_unitario_snapshot(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        talhao_id=area_id,
        quantidade_lote=100.0,
        data_referencia=data_colheita,
    )

    # Custo lançado depois da data de referência não deve entrar no acumulado —
    # sobra apenas a quantidade do próprio lote, custo acumulado fica em zero.
    assert resultado == 0.0


@pytest.mark.asyncio
async def test_produto_colhido_service_grava_snapshot_na_criacao(session: AsyncSession):
    """ProdutoColhidoService.criar (entrada manual de produção) é o segundo ponto
    de integração do snapshot — RomaneioService.criar também chama o mesmo helper
    (ver agricola/romaneios/service.py), mas hoje não há como testá-lo de ponta a
    ponta: RomaneioColheitaCreate não expõe commodity_id e Safra não carrega mais
    commodity_id (migrou para Cultivo) — limitação pré-existente, fora de escopo."""
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    unidade_ha_id = await _garantir_unidade_ha(session, tenant_id)

    from core.cadastros.commodities.models import Commodity
    from agricola.colheita.schemas import ProdutoColhidoCreate
    from agricola.colheita.service import ProdutoColhidoService

    commodity = Commodity(
        tenant_id=tenant_id,
        sistema=False,
        nome="Soja Snapshot",
        codigo=f"CMD-{str(uuid.uuid4())[:8]}",
        tipo="AGRICOLA",
        unidade_padrao="SACA_60KG",
        peso_unidade=60.0,
        umidade_padrao_pct=14.0,
        impureza_padrao_pct=1.0,
        possui_cotacao=False,
        ativo=True,
    )
    session.add(commodity)
    await session.commit()
    await session.refresh(commodity)

    hoje = date.today()
    await _registrar_custo_operacao(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        pu_id=pu.id,
        unidade_ha_id=unidade_ha_id,
        valor=1200.0,
        data=hoje,
    )

    produto_colhido = await ProdutoColhidoService(session, tenant_id).criar(
        ProdutoColhidoCreate(
            safra_id=safra.id,
            talhao_id=area_id,
            commodity_id=commodity.id,
            quantidade=100.0,
            unidade="SACA_60KG",
            peso_liquido_kg=6000.0,
            data_entrada=hoje,
            status="ARMAZENADO",
        )
    )
    await session.commit()

    assert produto_colhido.custo_unitario_producao is not None
    assert float(produto_colhido.custo_unitario_producao) == 12.0
