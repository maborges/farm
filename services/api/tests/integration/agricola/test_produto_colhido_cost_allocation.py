from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError
from agricola.colheita.models import ProdutoColhido
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.custos.lote_allocation_service import (
    aplicar_override_manual,
    obter_custo_alocado,
    reconciliar_alocacoes_lote,
)
from agricola.custos.models import ProdutoColhidoCostAllocation
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
        descricao="Operação com custo para rateio persistido",
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
    alloc = await registrar_cost_allocation(
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
    return alloc


async def _criar_lote(session, *, tenant_id, safra_id, talhao_id, commodity_id, quantidade, data) -> ProdutoColhido:
    lote = ProdutoColhido(
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        commodity_id=commodity_id,
        quantidade=quantidade,
        unidade="SACA_60KG",
        peso_liquido_kg=quantidade * 60.0,
        data_entrada=data,
        status="ARMAZENADO",
    )
    session.add(lote)
    await session.commit()
    await session.refresh(lote)
    return lote


async def _criar_commodity(session, tenant_id):
    from core.cadastros.commodities.models import Commodity

    commodity = Commodity(
        tenant_id=tenant_id,
        sistema=False,
        nome="Soja Cost Allocation",
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
    return commodity


async def _contexto_com_dois_lotes(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    unidade_ha_id = await _garantir_unidade_ha(session, tenant_id)
    commodity = await _criar_commodity(session, tenant_id)

    hoje = date.today()
    alloc = await _registrar_custo_operacao(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        pu_id=pu.id,
        unidade_ha_id=unidade_ha_id,
        valor=500.0,
        data=hoje,
    )

    lote_a = await _criar_lote(
        session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
        commodity_id=commodity.id, quantidade=60.0, data=hoje,
    )
    lote_b = await _criar_lote(
        session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
        commodity_id=commodity.id, quantidade=40.0, data=hoje,
    )
    return {"safra": safra, "area_id": area_id, "pu": pu, "alloc": alloc, "lote_a": lote_a, "lote_b": lote_b}


@pytest.mark.asyncio
async def test_reconciliacao_rateia_proporcional_e_soma_bate_com_custo_total(session: AsyncSession):
    tenant_id = uuid.uuid4()
    ctx = await _contexto_com_dois_lotes(session, tenant_id)

    itens_a = await reconciliar_alocacoes_lote(session, tenant_id, ctx["lote_a"].id)
    await session.commit()
    resumo_b = await obter_custo_alocado(session, tenant_id, ctx["lote_b"].id)

    assert len(itens_a) == 1
    assert float(itens_a[0].valor_atribuido) == 300.0
    assert resumo_b["total"] == 200.0
    assert round(float(itens_a[0].valor_atribuido) + resumo_b["total"], 2) == 500.0


@pytest.mark.asyncio
async def test_reconciliacao_e_idempotente(session: AsyncSession):
    tenant_id = uuid.uuid4()
    ctx = await _contexto_com_dois_lotes(session, tenant_id)

    await reconciliar_alocacoes_lote(session, tenant_id, ctx["lote_a"].id)
    await session.commit()
    await reconciliar_alocacoes_lote(session, tenant_id, ctx["lote_a"].id)
    await session.commit()

    todas = (
        await session.execute(
            select(ProdutoColhidoCostAllocation).where(
                ProdutoColhidoCostAllocation.tenant_id == tenant_id,
                ProdutoColhidoCostAllocation.produto_colhido_id.in_([ctx["lote_a"].id, ctx["lote_b"].id]),
            )
        )
    ).scalars().all()

    assert len(todas) == 2  # uma linha por lote, não duplica ao reconciliar de novo


@pytest.mark.asyncio
async def test_override_manual_nao_e_sobrescrito_pela_reconciliacao(session: AsyncSession):
    tenant_id = uuid.uuid4()
    ctx = await _contexto_com_dois_lotes(session, tenant_id)

    await reconciliar_alocacoes_lote(session, tenant_id, ctx["lote_a"].id)
    await session.commit()

    item_override = await aplicar_override_manual(
        session,
        tenant_id,
        ctx["lote_a"].id,
        ctx["alloc"].id,
        valor_atribuido=350.0,
        justificativa="Ajuste manual: lote A absorveu custo extra de secagem.",
    )
    await session.commit()
    assert item_override.origem_calculo == "MANUAL"
    assert float(item_override.valor_atribuido) == 350.0

    # Reconciliar de novo não deve sobrescrever a linha MANUAL do lote A,
    # mas deve recalcular normalmente a linha AUTOMATICO do lote B.
    await reconciliar_alocacoes_lote(session, tenant_id, ctx["lote_b"].id)
    await session.commit()

    resumo_a = await obter_custo_alocado(session, tenant_id, ctx["lote_a"].id)
    resumo_b = await obter_custo_alocado(session, tenant_id, ctx["lote_b"].id)

    assert resumo_a["total"] == 350.0
    assert any(item.origem_calculo == "MANUAL" for item in resumo_a["itens"])
    assert resumo_b["total"] == 200.0


@pytest.mark.asyncio
async def test_override_sem_justificativa_falha(session: AsyncSession):
    tenant_id = uuid.uuid4()
    ctx = await _contexto_com_dois_lotes(session, tenant_id)

    with pytest.raises(BusinessRuleError):
        await aplicar_override_manual(
            session,
            tenant_id,
            ctx["lote_a"].id,
            ctx["alloc"].id,
            valor_atribuido=100.0,
            justificativa="   ",
        )


@pytest.mark.asyncio
async def test_reconciliacao_falha_com_pu_ambiguo(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id, percentual=50.0)
    await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id, percentual=50.0)
    commodity = await _criar_commodity(session, tenant_id)

    lote = await _criar_lote(
        session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
        commodity_id=commodity.id, quantidade=50.0, data=date.today(),
    )

    with pytest.raises(BusinessRuleError):
        await reconciliar_alocacoes_lote(session, tenant_id, lote.id)
