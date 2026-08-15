from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.dre.service import DREAgricolaV1Service
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.production_units.models import ProductionUnit
from agricola.romaneios.models import RomaneioColheita
from agricola.safras.models import Safra
from core.cadastros.commodities.models import Commodity
from core.cadastros.pessoas.models import Pessoa
from core.models.unidade_produtiva import UnidadeProdutiva
from financeiro.comercializacao.models import ComercializacaoCommodity
from financeiro.models.despesa import Despesa
from financeiro.models.lancamento import LancamentoFinanceiro
from financeiro.models.plano_conta import PlanoConta
from financeiro.models.rateio import Rateio
from financeiro.models.receita import Receita
from operacional.models.estoque import EstoqueMovimento
from test_operational_workflow_governance_step02 import _garantir_unidade_ha
from test_operational_workflow_governance_step03 import _criar_area, _criar_cultivo, _criar_safra, _criar_unidade_produtiva, _garantir_tenant
from test_operational_workflow_governance_step05 import _criar_deposito, _criar_produto


async def _criar_plano_conta(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> PlanoConta:
    plano = PlanoConta(
        tenant_id=tenant_id,
        parent_id=None,
        codigo=f"8.13.{str(uuid.uuid4())[:8]}",
        nome=nome,
        tipo="DESPESA",
        natureza="ANALITICA",
        categoria_rfb="CUSTEIO",
        ordem=1,
        is_sistema=False,
        ativo=True,
    )
    session.add(plano)
    await session.commit()
    await session.refresh(plano)
    return plano


async def _criar_pessoa(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> Pessoa:
    pessoa = Pessoa(
        tenant_id=tenant_id,
        tipo="PF",
        nome_exibicao=nome,
        base_legal="CONTRATO",
        ativo=True,
    )
    session.add(pessoa)
    await session.commit()
    await session.refresh(pessoa)
    return pessoa


async def _criar_commodity(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> Commodity:
    commodity = Commodity(
        tenant_id=tenant_id,
        sistema=False,
        nome=nome,
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


async def _criar_production_unit_extra(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    cultivo_id: uuid.UUID,
    area_id: uuid.UUID,
) -> ProductionUnit:
    pu = ProductionUnit(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        percentual_participacao=100,
        area_ha=30.0,
        status="ATIVA",
    )
    session.add(pu)
    await session.commit()
    await session.refresh(pu)
    return pu


async def _base_contexto(session: AsyncSession, tenant_id: uuid.UUID, nome_up: str = "UP DRE"):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit_extra(session, tenant_id, safra.id, cultivo_id, area_id)
    produto = await _criar_produto(session, tenant_id)
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    unidade_ha_id = await _garantir_unidade_ha(session, tenant_id)
    return unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id


async def _criar_romaneio_e_receita(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    area_id: uuid.UUID,
    production_unit_id: uuid.UUID,
    commodity_id: uuid.UUID,
    plano_conta_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    data_colheita: date,
    peso_bruto_kg: float,
    tara_kg: float,
    peso_liquido_kg: float,
    sacas_60kg: float,
    preco_saca: float,
) -> tuple[RomaneioColheita, Receita]:
    romaneio = RomaneioColheita(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=None,
        production_unit_id=production_unit_id,
        talhao_id=area_id,
        commodity_id=commodity_id,
        data_colheita=data_colheita,
        peso_bruto_kg=peso_bruto_kg,
        tara_kg=tara_kg,
        peso_liquido_kg=peso_liquido_kg,
        desconto_umidade_kg=0.0,
        desconto_impureza_kg=0.0,
        peso_liquido_padrao_kg=peso_liquido_kg,
        sacas_60kg=sacas_60kg,
        preco_saca=preco_saca,
        receita_total=round(sacas_60kg * preco_saca, 2),
        destino="ARMAZEM",
    )
    session.add(romaneio)
    await session.flush()

    receita = Receita(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        plano_conta_id=plano_conta_id,
        descricao="Receita romaneio",
        valor_total=romaneio.receita_total,
        data_emissao=data_colheita,
        data_vencimento=data_colheita,
        status="RECEBIDO",
        origem_tipo="ROMANEIO_COLHEITA",
        origem_id=romaneio.id,
    )
    session.add(receita)

    produto_colhido = await session.execute(
        select(Commodity).where(Commodity.id == commodity_id)
    )
    commodity = produto_colhido.scalar_one()

    from agricola.colheita.models import ProdutoColhido

    session.add(
        ProdutoColhido(
            tenant_id=tenant_id,
            safra_id=safra_id,
            talhao_id=area_id,
            romaneio_id=romaneio.id,
            commodity_id=commodity.id,
            quantidade=sacas_60kg,
            unidade=commodity.unidade_padrao,
            peso_liquido_kg=peso_liquido_kg,
            data_entrada=data_colheita,
            destino="ARMAZENADO",
            status="ARMAZENADO",
        )
    )
    await session.commit()
    await session.refresh(romaneio)
    await session.refresh(receita)
    return romaneio, receita


async def _criar_despesa(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    plano_conta_id: uuid.UUID,
    descricao: str,
    valor_total: float,
    data_emissao: date,
    origem_tipo: str = "ABASTECIMENTO",
    origem_id: uuid.UUID | None = None,
) -> Despesa:
    despesa = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        plano_conta_id=plano_conta_id,
        descricao=descricao,
        valor_total=valor_total,
        data_emissao=data_emissao,
        data_vencimento=data_emissao,
        status="PAGO",
        origem_tipo=origem_tipo,
        origem_id=origem_id or uuid.uuid4(),
        ativo=True,
    )
    session.add(despesa)
    await session.flush()
    return despesa


@pytest.mark.asyncio
async def test_dre_v1_consolida_precedencia_e_nao_duplica_receita_rateio(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)
    commodity = await _criar_commodity(session, tenant_id, "Soja Step13")
    comprador = await _criar_pessoa(session, tenant_id, "Comprador Step13")
    plano_receita = await _criar_plano_conta(session, tenant_id, "Plano Receita DRE")
    plano_despesa = await _criar_plano_conta(session, tenant_id, "Plano Despesa DRE")

    _, receita_rom = await _criar_romaneio_e_receita(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        area_id=area_id,
        production_unit_id=pu.id,
        commodity_id=commodity.id,
        plano_conta_id=plano_receita.id,
        unidade_produtiva_id=unidade_id,
        data_colheita=date.today(),
        peso_bruto_kg=6000.0,
        tara_kg=0.0,
        peso_liquido_kg=6000.0,
        sacas_60kg=100.0,
        preco_saca=100.0,
    )

    from agricola.colheita.models import ProdutoColhido

    produto_colhido = (
        await session.execute(
            select(ProdutoColhido).where(
                ProdutoColhido.tenant_id == tenant_id,
                ProdutoColhido.romaneio_id == receita_rom.origem_id,
            )
        )
    ).scalars().first()

    comercializacao = ComercializacaoCommodity(
        tenant_id=tenant_id,
        commodity_id=commodity.id,
        comprador_id=comprador.id,
        quantidade=50.0,
        unidade="SACA_60KG",
        preco_unitario=120.0,
        moeda="BRL",
        forma_pagamento="PRAZO",
        produto_colhido_id=produto_colhido.id,
        status="CONFIRMADO",
        valor_total=6000.0,
    )
    session.add(comercializacao)
    await session.flush()

    receita_comm = Receita(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_receita.id,
        descricao="Receita comercialização",
        valor_total=6000.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="A_RECEBER",
        origem_tipo="COMERCIALIZACAO",
        origem_id=comercializacao.id,
    )
    session.add(receita_comm)

    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação com custo direto",
        data_realizada=date.today(),
        custo_total=2500.0,
        custo_por_ha=83.33,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.flush()
    execucao = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao.id,
        production_unit_id=pu.id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id,
        custo_real=2500.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add(execucao)
    await session.flush()
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="OPERATION_EXECUTION",
        source_id=execucao.id,
        operation_execution_id=execucao.id,
        amount=2500.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )

    despesa_operacional = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_despesa.id,
        descricao="Despesa operacional sem allocation",
        valor_total=150.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="ABASTECIMENTO",
        origem_id=uuid.uuid4(),
        ativo=True,
    )
    session.add(despesa_operacional)

    despesa_rateio = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_despesa.id,
        descricao="Despesa rateada",
        valor_total=300.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        # O rateio é a ponte oficial de apropriação; a despesa não precisa
        # carregar uma origem artificial para ser deduplicada na DRE.
        origem_tipo=None,
        origem_id=None,
        ativo=True,
    )
    session.add(despesa_rateio)
    await session.flush()
    rateio = Rateio(
        tenant_id=tenant_id,
        despesa_id=despesa_rateio.id,
        safra_id=safra.id,
        talhao_id=area_id,
        valor_rateado=300.0,
        percentual=100.0,
    )
    session.add(rateio)
    await session.flush()
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="FIN_RATEIO",
        source_id=rateio.id,
        fin_rateio_id=rateio.id,
        amount=300.0,
        allocation_date=date.today(),
        cost_category="DESPESA_FINANCEIRA",
        allocation_method="DIRECT",
    )

    lancamento_financeiro = LancamentoFinanceiro(
        tenant_id=tenant_id,
        safra_id=safra.id,
        descricao="Caixa da comercialização",
        valor=6000.0,
        data=date.today(),
        tipo="RECEITA",
        categoria="VENDA_PRODUCAO",
        origem="COMERCIALIZACAO",
        origem_id=comercializacao.id,
    )
    session.add(lancamento_financeiro)
    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra.id,
        unidade_produtiva_id=unidade_id,
    )

    assert dre.receita_bruta == 11000.0
    assert dre.deducoes == 0.0
    assert dre.receita_liquida == 11000.0
    assert dre.custos_diretos == 2500.0
    assert dre.custos_operacionais == 300.0
    assert dre.despesas_operacionais == 150.0
    assert dre.margem_bruta == 8500.0
    assert dre.resultado_operacional == 8050.0
    assert dre.kpis.area_total_ha == 30.0
    assert dre.kpis.receita_liquida == 11000.0
    assert dre.kpis.custo_operacional_total == 2950.0
    assert dre.kpis.margem_bruta == 8500.0
    assert dre.kpis.resultado_operacional == 8050.0
    assert dre.kpis.margem_pct == pytest.approx(73.18, abs=0.01)
    assert dre.kpis.custo_por_hectare == pytest.approx(98.33, abs=0.01)
    assert dre.kpis.receita_por_hectare == pytest.approx(366.67, abs=0.01)
    assert dre.kpis.resultado_por_hectare == pytest.approx(268.33, abs=0.01)
    # SOIL-PLAN-EXEC-04I: CostAllocation(OPERATION_EXECUTION) sem Despesa(OPERACAO_AGRICOLA)
    # deixou de ser um risco de reconciliação — é o estado normal para operações novas.
    assert dre.kpis.sujeito_reconciliacao is False
    assert "CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO" not in dre.kpis.warnings_relevantes
    assert any(item.origem_tipo == "COMERCIALIZACAO" for item in dre.receita.itens)
    saldo_romaneio = next(item for item in dre.receita.itens if item.origem_tipo == "ROMANEIO_COLHEITA")
    assert saldo_romaneio.valor == 5000.0
    assert saldo_romaneio.meta["saldo_percentual"] == 0.5
    assert any(item.origem_tipo == "FIN_RATEIO" for item in dre.custos_operacionais_detalhe.itens)
    assert not any(item.meta.get("despesa_id") == str(despesa_rateio.id) for item in dre.despesas_operacionais_detalhe.itens)


@pytest.mark.asyncio
async def test_dre_v1_filtra_production_unit_e_isola_tenant(session: AsyncSession):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    unidade_a, area_a, safra_a, cultivo_a, pu_a, produto_a, deposito_a, unidade_ha_id_a = await _base_contexto(session, tenant_a)
    unidade_b, area_b, safra_b, cultivo_b, pu_b, produto_b, deposito_b, unidade_ha_id_b = await _base_contexto(session, tenant_b)

    commodity_a = await _criar_commodity(session, tenant_a, "Commodity A")
    commodity_b = await _criar_commodity(session, tenant_b, "Commodity B")
    comprador_a = await _criar_pessoa(session, tenant_a, "Comprador A")
    comprador_b = await _criar_pessoa(session, tenant_b, "Comprador B")
    plano_a = await _criar_plano_conta(session, tenant_a, "Plano A")
    plano_b = await _criar_plano_conta(session, tenant_b, "Plano B")

    await _criar_romaneio_e_receita(
        session,
        tenant_id=tenant_a,
        safra_id=safra_a.id,
        area_id=area_a,
        production_unit_id=pu_a.id,
        commodity_id=commodity_a.id,
        plano_conta_id=plano_a.id,
        unidade_produtiva_id=unidade_a,
        data_colheita=date.today(),
        peso_bruto_kg=3000.0,
        tara_kg=0.0,
        peso_liquido_kg=3000.0,
        sacas_60kg=50.0,
        preco_saca=100.0,
    )
    await _criar_romaneio_e_receita(
        session,
        tenant_id=tenant_b,
        safra_id=safra_b.id,
        area_id=area_b,
        production_unit_id=pu_b.id,
        commodity_id=commodity_b.id,
        plano_conta_id=plano_b.id,
        unidade_produtiva_id=unidade_b,
        data_colheita=date.today(),
        peso_bruto_kg=4000.0,
        tara_kg=0.0,
        peso_liquido_kg=4000.0,
        sacas_60kg=40.0,
        preco_saca=120.0,
    )

    operacao_a = OperacaoAgricola(
        tenant_id=tenant_a,
        safra_id=safra_a.id,
        cultivo_id=cultivo_a,
        production_unit_id=pu_a.id,
        talhao_id=area_a,
        tipo="PLANTIO",
        descricao="Operação A",
        data_realizada=date.today(),
        custo_total=1000.0,
        custo_por_ha=33.33,
        status="REALIZADA",
    )
    operacao_b = OperacaoAgricola(
        tenant_id=tenant_b,
        safra_id=safra_b.id,
        cultivo_id=cultivo_b,
        production_unit_id=pu_b.id,
        talhao_id=area_b,
        tipo="PLANTIO",
        descricao="Operação B",
        data_realizada=date.today(),
        custo_total=2000.0,
        custo_por_ha=66.66,
        status="REALIZADA",
    )
    session.add_all([operacao_a, operacao_b])
    await session.flush()
    exec_a = OperacaoExecucao(
        tenant_id=tenant_a,
        operacao_id=operacao_a.id,
        production_unit_id=pu_a.id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id_a,
        custo_real=1000.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    exec_b = OperacaoExecucao(
        tenant_id=tenant_b,
        operacao_id=operacao_b.id,
        production_unit_id=pu_b.id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id_b,
        custo_real=2000.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add_all([exec_a, exec_b])
    await session.flush()
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_a,
        production_unit_id=pu_a.id,
        source="OPERATION_EXECUTION",
        source_id=exec_a.id,
        operation_execution_id=exec_a.id,
        amount=1000.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_b,
        production_unit_id=pu_b.id,
        source="OPERATION_EXECUTION",
        source_id=exec_b.id,
        operation_execution_id=exec_b.id,
        amount=2000.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await session.commit()

    dre_a = await DREAgricolaV1Service(session, tenant_a).gerar(
        safra_id=safra_a.id,
        production_unit_id=pu_a.id,
    )

    assert dre_a.receita_bruta == 5000.0
    assert dre_a.custos_diretos == 1000.0
    assert pu_b.id not in dre_a.production_unit_ids
    assert all(item.production_unit_id == pu_a.id for item in dre_a.custos_diretos_detalhe.itens)


@pytest.mark.asyncio
async def test_dre_v1_warnings_reconciliacao_estoque_sem_allocation(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)

    mov = EstoqueMovimento(
        tenant_id=tenant_id,
        data_movimento=date.today(),
        tipo_movimento="ENTRADA",
        produto_id=produto.id,
        deposito_id=deposito.id,
        lote_id=None,
        quantidade=10.0,
        unidade_medida_id=unidade_ha_id,
        custo_unitario=25.0,
        custo_total=250.0,
        origem="COMPRA",
        origem_id=uuid.uuid4(),
        production_unit_id=pu.id,
        observacoes="Movimento sem allocation",
    )
    session.add(mov)
    session.add(
        LancamentoFinanceiro(
            tenant_id=tenant_id,
            safra_id=safra.id,
            descricao="Reflexo financeiro do movimento",
            valor=250.0,
            data=date.today(),
            tipo="CUSTO",
            categoria="OPERACOES",
            origem="ESTOQUE",
            origem_id=mov.id,
        )
    )
    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra.id,
        production_unit_id=pu.id,
    )

    assert any(w.codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" for w in dre.warnings)
    assert dre.reconciliacao.estoque_movimentos_com_custo == 1
    assert dre.kpis.sujeito_reconciliacao is True
    assert "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" in dre.kpis.warnings_relevantes


@pytest.mark.asyncio
async def test_dre_v1_aplica_recorte_temporal_sem_quebrar_precedencia(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)
    commodity = await _criar_commodity(session, tenant_id, "Commodity Periodo")
    comprador = await _criar_pessoa(session, tenant_id, "Comprador Periodo")
    plano_receita = await _criar_plano_conta(session, tenant_id, "Plano Receita Periodo")
    plano_despesa = await _criar_plano_conta(session, tenant_id, "Plano Despesa Periodo")

    inicio = date(2026, 1, 1)
    fim = date(2026, 1, 31)

    await _criar_romaneio_e_receita(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        area_id=area_id,
        production_unit_id=pu.id,
        commodity_id=commodity.id,
        plano_conta_id=plano_receita.id,
        unidade_produtiva_id=unidade_id,
        data_colheita=date(2026, 1, 10),
        peso_bruto_kg=6000.0,
        tara_kg=0.0,
        peso_liquido_kg=6000.0,
        sacas_60kg=100.0,
        preco_saca=100.0,
    )
    await _criar_romaneio_e_receita(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        area_id=area_id,
        production_unit_id=pu.id,
        commodity_id=commodity.id,
        plano_conta_id=plano_receita.id,
        unidade_produtiva_id=unidade_id,
        data_colheita=date(2026, 2, 10),
        peso_bruto_kg=3000.0,
        tara_kg=0.0,
        peso_liquido_kg=3000.0,
        sacas_60kg=50.0,
        preco_saca=90.0,
    )

    operacao_in = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação no período",
        data_realizada=date(2026, 1, 12),
        custo_total=250.0,
        custo_por_ha=5.0,
        status="REALIZADA",
    )
    operacao_out = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação fora do período",
        data_realizada=date(2026, 2, 12),
        custo_total=500.0,
        custo_por_ha=10.0,
        status="REALIZADA",
    )
    session.add_all([operacao_in, operacao_out])
    await session.flush()

    execucao_in = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao_in.id,
        production_unit_id=pu.id,
        data_execucao=date(2026, 1, 12),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id,
        custo_real=250.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    execucao_out = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao_out.id,
        production_unit_id=pu.id,
        data_execucao=date(2026, 2, 12),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id,
        custo_real=500.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add_all([execucao_in, execucao_out])
    await session.flush()

    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="OPERATION_EXECUTION",
        source_id=execucao_in.id,
        operation_execution_id=execucao_in.id,
        amount=250.0,
        allocation_date=date(2026, 1, 12),
        cost_category="OUTROS",
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="OPERATION_EXECUTION",
        source_id=execucao_out.id,
        operation_execution_id=execucao_out.id,
        amount=500.0,
        allocation_date=date(2026, 2, 12),
        cost_category="OUTROS",
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )

    await _criar_despesa(
        session,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_despesa.id,
        descricao="Despesa no período",
        valor_total=150.0,
        data_emissao=date(2026, 1, 20),
        origem_tipo="ABASTECIMENTO",
    )
    await _criar_despesa(
        session,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_despesa.id,
        descricao="Despesa fora do período",
        valor_total=275.0,
        data_emissao=date(2026, 2, 20),
        origem_tipo="ABASTECIMENTO",
    )

    session.add(
        LancamentoFinanceiro(
            tenant_id=tenant_id,
            safra_id=safra.id,
            descricao="Lançamento financeiro no período",
            valor=1000.0,
            data=date(2026, 1, 25),
            tipo="RECEITA",
            categoria="VENDA_PRODUCAO",
            origem="COMERCIALIZACAO",
            origem_id=uuid.uuid4(),
        )
    )
    session.add(
        LancamentoFinanceiro(
            tenant_id=tenant_id,
            safra_id=safra.id,
            descricao="Lançamento financeiro fora do período",
            valor=800.0,
            data=date(2026, 2, 25),
            tipo="CUSTO",
            categoria="OPERACOES",
            origem="ESTOQUE",
            origem_id=uuid.uuid4(),
        )
    )
    session.add(
        EstoqueMovimento(
            tenant_id=tenant_id,
            data_movimento=datetime(2026, 1, 18, 12, 0, tzinfo=timezone.utc),
            tipo_movimento="ENTRADA",
            produto_id=produto.id,
            deposito_id=deposito.id,
            lote_id=None,
            quantidade=10.0,
            unidade_medida_id=unidade_ha_id,
            custo_unitario=25.0,
            custo_total=250.0,
            origem="COMPRA",
            origem_id=uuid.uuid4(),
            production_unit_id=pu.id,
            observacoes="Movimento dentro do período sem allocation",
        )
    )
    session.add(
        EstoqueMovimento(
            tenant_id=tenant_id,
            data_movimento=datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc),
            tipo_movimento="ENTRADA",
            produto_id=produto.id,
            deposito_id=deposito.id,
            lote_id=None,
            quantidade=5.0,
            unidade_medida_id=unidade_ha_id,
            custo_unitario=50.0,
            custo_total=250.0,
            origem="COMPRA",
            origem_id=uuid.uuid4(),
            production_unit_id=pu.id,
            observacoes="Movimento fora do período sem allocation",
        )
    )
    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra.id,
        unidade_produtiva_id=unidade_id,
        production_unit_id=pu.id,
        data_inicio=inicio,
        data_fim=fim,
    )

    assert dre.safra_id == safra.id
    assert dre.production_unit_ids == [pu.id]
    assert dre.receita_bruta == 10000.0
    assert dre.custos_diretos == 250.0
    assert dre.despesas_operacionais == 150.0
    assert dre.receita.total_registros == 1
    assert dre.custos_diretos_detalhe.total_registros == 1
    assert dre.despesas_operacionais_detalhe.total_registros == 1
    assert all(item.meta.get("data_economica") == "2026-01-10" for item in dre.receita.itens)
    assert all(item.meta.get("data_economica_fonte") == "competencia" or item.meta.get("data_economica_fonte") == "data_emissao" for item in dre.despesas_operacionais_detalhe.itens)
    assert dre.reconciliacao.lancamentos_financeiros_receita == 1000.0
    assert dre.reconciliacao.lancamentos_financeiros_custo == 0.0
    assert dre.reconciliacao.cost_allocations_total == 1
    assert dre.reconciliacao.estoque_movimentos_com_custo == 1
    assert dre.reconciliacao.detalhes["periodo"] == {
        "data_inicio": "2026-01-01",
        "data_fim": "2026-01-31",
    }
    assert any(w.codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" for w in dre.warnings)
    movimento_warning = next(w for w in dre.warnings if w.codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION")
    assert movimento_warning.meta["quantidade"] == 1


@pytest.mark.asyncio
async def test_dre_v1_zerada_quando_nao_houver_dados_validos(session: AsyncSession):
    tenant_id = uuid.uuid4()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar()

    assert dre.tenant_id == tenant_id
    assert dre.receita_bruta == 0.0
    assert dre.deducoes == 0.0
    assert dre.receita_liquida == 0.0
    assert dre.custos_diretos == 0.0
    assert dre.custos_operacionais == 0.0
    assert dre.despesas_operacionais == 0.0
    assert dre.resultado_operacional == 0.0
    assert dre.production_unit_ids == []
    assert dre.receita.total_registros == 0
    assert dre.custos_diretos_detalhe.total_registros == 0
    assert dre.custos_operacionais_detalhe.total_registros == 0
    assert dre.despesas_operacionais_detalhe.total_registros == 0
    assert dre.warnings == []


@pytest.mark.asyncio
async def test_dre_v1_filtra_por_safra_e_isola_production_unit(session: AsyncSession):
    tenant_id = uuid.uuid4()

    unidade_a, area_a, safra_a, cultivo_a, pu_a, produto_a, deposito_a, unidade_ha_id_a = await _base_contexto(session, tenant_id)
    unidade_b, area_b, safra_b, cultivo_b, pu_b, produto_b, deposito_b, unidade_ha_id_b = await _base_contexto(session, tenant_id)

    commodity_a = await _criar_commodity(session, tenant_id, "Commodity Safra A")
    commodity_b = await _criar_commodity(session, tenant_id, "Commodity Safra B")
    comprador_a = await _criar_pessoa(session, tenant_id, "Comprador Safra A")
    comprador_b = await _criar_pessoa(session, tenant_id, "Comprador Safra B")
    plano_receita_a = await _criar_plano_conta(session, tenant_id, "Plano Receita Safra A")
    plano_receita_b = await _criar_plano_conta(session, tenant_id, "Plano Receita Safra B")

    await _criar_romaneio_e_receita(
        session,
        tenant_id=tenant_id,
        safra_id=safra_a.id,
        area_id=area_a,
        production_unit_id=pu_a.id,
        commodity_id=commodity_a.id,
        plano_conta_id=plano_receita_a.id,
        unidade_produtiva_id=unidade_a,
        data_colheita=date.today(),
        peso_bruto_kg=4000.0,
        tara_kg=0.0,
        peso_liquido_kg=4000.0,
        sacas_60kg=60.0,
        preco_saca=100.0,
    )
    await _criar_romaneio_e_receita(
        session,
        tenant_id=tenant_id,
        safra_id=safra_b.id,
        area_id=area_b,
        production_unit_id=pu_b.id,
        commodity_id=commodity_b.id,
        plano_conta_id=plano_receita_b.id,
        unidade_produtiva_id=unidade_b,
        data_colheita=date.today(),
        peso_bruto_kg=8000.0,
        tara_kg=0.0,
        peso_liquido_kg=8000.0,
        sacas_60kg=120.0,
        preco_saca=120.0,
    )

    operacao_a = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra_a.id,
        cultivo_id=cultivo_a,
        production_unit_id=pu_a.id,
        talhao_id=area_a,
        tipo="PLANTIO",
        descricao="Operação safra A",
        data_realizada=date.today(),
        custo_total=1000.0,
        custo_por_ha=20.0,
        status="REALIZADA",
    )
    operacao_b = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra_b.id,
        cultivo_id=cultivo_b,
        production_unit_id=pu_b.id,
        talhao_id=area_b,
        tipo="PLANTIO",
        descricao="Operação safra B",
        data_realizada=date.today(),
        custo_total=2000.0,
        custo_por_ha=40.0,
        status="REALIZADA",
    )
    session.add_all([operacao_a, operacao_b])
    await session.flush()

    execucao_a = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao_a.id,
        production_unit_id=pu_a.id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id_a,
        custo_real=1000.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    execucao_b = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao_b.id,
        production_unit_id=pu_b.id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id_b,
        custo_real=2000.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add_all([execucao_a, execucao_b])
    await session.flush()

    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu_a.id,
        source="OPERATION_EXECUTION",
        source_id=execucao_a.id,
        operation_execution_id=execucao_a.id,
        amount=1000.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu_b.id,
        source="OPERATION_EXECUTION",
        source_id=execucao_b.id,
        operation_execution_id=execucao_b.id,
        amount=2000.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra_a.id,
        production_unit_id=pu_a.id,
    )

    assert dre.safra_id == safra_a.id
    assert dre.production_unit_ids == [pu_a.id]
    assert dre.receita_bruta == 6000.0
    assert dre.custos_diretos == 1000.0
    assert pu_b.id not in dre.production_unit_ids
    assert all(item.production_unit_id == pu_a.id for item in dre.receita.itens)
    assert all(item.safra_id == safra_a.id for item in dre.receita.itens)
    assert all(item.production_unit_id == pu_a.id for item in dre.custos_diretos_detalhe.itens)


@pytest.mark.asyncio
async def test_dre_v1_nao_duplica_lancamento_financeiro_com_mesmo_evento(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)
    commodity = await _criar_commodity(session, tenant_id, "Commodity LF")
    comprador = await _criar_pessoa(session, tenant_id, "Comprador LF")
    plano_receita = await _criar_plano_conta(session, tenant_id, "Plano Receita LF")
    plano_despesa = await _criar_plano_conta(session, tenant_id, "Plano Despesa LF")

    _, receita_rom = await _criar_romaneio_e_receita(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        area_id=area_id,
        production_unit_id=pu.id,
        commodity_id=commodity.id,
        plano_conta_id=plano_receita.id,
        unidade_produtiva_id=unidade_id,
        data_colheita=date.today(),
        peso_bruto_kg=5000.0,
        tara_kg=0.0,
        peso_liquido_kg=5000.0,
        sacas_60kg=80.0,
        preco_saca=100.0,
    )

    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação base da despesa",
        data_realizada=date.today(),
        custo_total=150.0,
        custo_por_ha=3.0,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.flush()

    despesa = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_despesa.id,
        descricao="Despesa operacional com reflexo financeiro",
        valor_total=150.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="OPERACAO_AGRICOLA",
        origem_id=operacao.id,
        ativo=True,
    )
    session.add(despesa)

    lancamento_receita = LancamentoFinanceiro(
        tenant_id=tenant_id,
        safra_id=safra.id,
        descricao="Caixa da comercialização",
        valor=receita_rom.valor_total,
        data=date.today(),
        tipo="RECEITA",
        categoria="VENDA_PRODUCAO",
        origem="COMERCIALIZACAO",
        origem_id=receita_rom.origem_id,
    )
    lancamento_despesa = LancamentoFinanceiro(
        tenant_id=tenant_id,
        safra_id=safra.id,
        descricao="Caixa da despesa",
        valor=150.0,
        data=date.today(),
        tipo="CUSTO",
        categoria="OPERACOES",
        origem="DESPESA",
        origem_id=despesa.id,
    )
    session.add_all([lancamento_receita, lancamento_despesa])
    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra.id,
        production_unit_id=pu.id,
    )

    assert dre.receita_bruta == float(receita_rom.valor_total)
    assert dre.despesas_operacionais == 150.0
    assert dre.receita_liquida < dre.receita_bruta
    assert dre.reconciliacao.lancamentos_financeiros_receita == float(receita_rom.valor_total)
    assert dre.reconciliacao.lancamentos_financeiros_custo == 150.0
    assert dre.reconciliacao.lancamentos_financeiros_total == float(receita_rom.valor_total) - 150.0


@pytest.mark.asyncio
async def test_dre_v1_costallocation_prevalece_sobre_estoque_movimento(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)

    mov = EstoqueMovimento(
        tenant_id=tenant_id,
        data_movimento=date.today(),
        tipo_movimento="ENTRADA",
        produto_id=produto.id,
        deposito_id=deposito.id,
        lote_id=None,
        quantidade=10.0,
        unidade_medida_id=unidade_ha_id,
        custo_unitario=25.0,
        custo_total=250.0,
        origem="COMPRA",
        origem_id=uuid.uuid4(),
        production_unit_id=pu.id,
        observacoes="Movimento com allocation",
    )
    session.add(mov)
    await session.flush()

    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="INVENTORY_MOVEMENT",
        source_id=mov.id,
        inventory_movement_id=mov.id,
        amount=250.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra.id,
        production_unit_id=pu.id,
    )

    assert dre.custos_diretos == 250.0
    assert dre.custos_diretos_detalhe.total_registros == 1
    assert all(item.fonte_oficial == "CostAllocation" for item in dre.custos_diretos_detalhe.itens)
    assert not any(w.codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" for w in dre.warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "consumo_amount,custo_esperado",
    [
        (None, 0.0),
        (2000.0, 2000.0),
        (10000.0, 10000.0),
    ],
)
async def test_dre_v1_exclui_despesa_compra_incondicionalmente(
    session: AsyncSession, consumo_amount: float | None, custo_esperado: float
):
    """Despesa(origem_tipo=COMPRA) nunca entra na DRE; o custo agrícola vem de CostAllocation."""
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)
    plano_despesa = await _criar_plano_conta(session, tenant_id, "Plano Despesa Compra")

    await _criar_despesa(
        session,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_despesa.id,
        descricao="Compra de insumo",
        valor_total=10000.0,
        data_emissao=date.today(),
        origem_tipo="COMPRA",
    )

    if consumo_amount is not None:
        mov = EstoqueMovimento(
            tenant_id=tenant_id,
            data_movimento=date.today(),
            tipo_movimento="ENTRADA",
            produto_id=produto.id,
            deposito_id=deposito.id,
            lote_id=None,
            quantidade=1.0,
            unidade_medida_id=unidade_ha_id,
            custo_unitario=consumo_amount,
            custo_total=consumo_amount,
            origem="COMPRA",
            origem_id=uuid.uuid4(),
            production_unit_id=pu.id,
            observacoes="Consumo FIFO",
        )
        session.add(mov)
        await session.flush()
        await registrar_cost_allocation(
            session,
            tenant_id=tenant_id,
            production_unit_id=pu.id,
            source="INVENTORY_MOVEMENT",
            source_id=mov.id,
            inventory_movement_id=mov.id,
            amount=consumo_amount,
            allocation_date=date.today(),
            cost_category="INSUMO",
            allocation_method="DIRECT",
        )

    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra.id,
        production_unit_id=pu.id,
    )

    assert dre.despesas_operacionais == 0.0
    assert not any(item.origem_tipo == "COMPRA" for item in dre.despesas_operacionais_detalhe.itens)
    assert dre.custos_diretos == custo_esperado
    assert dre.resultado_operacional == -custo_esperado


@pytest.mark.asyncio
async def test_dre_v1_preserva_fallback_historico_despesa_operacao_sem_allocation(
    session: AsyncSession,
):
    """SOIL-PLAN-EXEC-04I: operações novas não criam mais Despesa(OPERACAO_AGRICOLA) — o
    custo vem exclusivamente de CostAllocation. Este teste documenta explicitamente que a
    regra de precedência da DRE (excluir despesa apenas quando existe CostAllocation
    correspondente) é mantida por COMPATIBILIDADE HISTÓRICA: uma Despesa(OPERACAO_AGRICOLA)
    legada (criada antes de 04I), sem CostAllocation vinculado, ainda é reconhecida como
    custo — nenhuma nova despesa desse tipo deve ser criada para produzir esse efeito."""
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = (
        await _base_contexto(session, tenant_id)
    )
    plano_despesa = await _criar_plano_conta(session, tenant_id, "Plano Despesa Historica")

    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação histórica sem CostAllocation",
        data_realizada=date.today(),
        custo_total=900.0,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.flush()

    await _criar_despesa(
        session,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_despesa.id,
        descricao="Despesa histórica pré-04I",
        valor_total=900.0,
        data_emissao=date.today(),
        origem_tipo="OPERACAO_AGRICOLA",
        origem_id=operacao.id,
    )
    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra.id,
        production_unit_id=pu.id,
    )

    assert dre.custos_diretos == 0.0
    assert dre.despesas_operacionais == 900.0
    assert any(
        item.origem_id == operacao.id and item.origem_tipo == "OPERACAO_AGRICOLA"
        for item in dre.despesas_operacionais_detalhe.itens
    )


@pytest.mark.asyncio
async def test_dre_v1_rateia_custo_por_lote_proporcional_a_quantidade(session: AsyncSession):
    """OPERATIONS-GAP-01: o custo da PU deve ser rateado entre os lotes vendidos
    proporcionalmente à quantidade, e uma comercialização sem produto_colhido_id deve
    ser reportada como lote sem vínculo, sem quebrar a DRE agregada."""
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)
    commodity = await _criar_commodity(session, tenant_id, "Soja Lote Margem")
    comprador = await _criar_pessoa(session, tenant_id, "Comprador Lote Margem")
    plano_receita = await _criar_plano_conta(session, tenant_id, "Plano Receita Lote Margem")

    from agricola.colheita.models import ProdutoColhido

    # Dois lotes na mesma PU, com quantidades diferentes (60 e 40 sacas).
    lote_a = ProdutoColhido(
        tenant_id=tenant_id,
        safra_id=safra.id,
        talhao_id=area_id,
        romaneio_id=None,
        commodity_id=commodity.id,
        quantidade=60.0,
        unidade=commodity.unidade_padrao,
        peso_liquido_kg=3600.0,
        data_entrada=date.today(),
        destino="ARMAZENADO",
        status="VENDIDO",
    )
    lote_b = ProdutoColhido(
        tenant_id=tenant_id,
        safra_id=safra.id,
        talhao_id=area_id,
        romaneio_id=None,
        commodity_id=commodity.id,
        quantidade=40.0,
        unidade=commodity.unidade_padrao,
        peso_liquido_kg=2400.0,
        data_entrada=date.today(),
        destino="ARMAZENADO",
        status="VENDIDO",
    )
    session.add_all([lote_a, lote_b])
    await session.flush()

    comercializacao_a = ComercializacaoCommodity(
        tenant_id=tenant_id,
        commodity_id=commodity.id,
        comprador_id=comprador.id,
        quantidade=60.0,
        unidade="SACA_60KG",
        preco_unitario=100.0,
        moeda="BRL",
        forma_pagamento="PRAZO",
        produto_colhido_id=lote_a.id,
        status="CONFIRMADO",
        valor_total=6000.0,
    )
    comercializacao_b = ComercializacaoCommodity(
        tenant_id=tenant_id,
        commodity_id=commodity.id,
        comprador_id=comprador.id,
        quantidade=40.0,
        unidade="SACA_60KG",
        preco_unitario=100.0,
        moeda="BRL",
        forma_pagamento="PRAZO",
        produto_colhido_id=lote_b.id,
        status="CONFIRMADO",
        valor_total=4000.0,
    )
    # Comercialização sem lote vinculado — deve aparecer só como aviso, fora do rateio.
    comercializacao_sem_lote = ComercializacaoCommodity(
        tenant_id=tenant_id,
        commodity_id=commodity.id,
        comprador_id=comprador.id,
        quantidade=10.0,
        unidade="SACA_60KG",
        preco_unitario=100.0,
        moeda="BRL",
        forma_pagamento="PRAZO",
        produto_colhido_id=None,
        status="CONFIRMADO",
        valor_total=1000.0,
    )
    session.add_all([comercializacao_a, comercializacao_b, comercializacao_sem_lote])
    await session.flush()

    session.add_all([
        Receita(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_id,
            plano_conta_id=plano_receita.id,
            descricao="Receita lote A",
            valor_total=6000.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            status="A_RECEBER",
            origem_tipo="COMERCIALIZACAO",
            origem_id=comercializacao_a.id,
        ),
        Receita(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_id,
            plano_conta_id=plano_receita.id,
            descricao="Receita lote B",
            valor_total=4000.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            status="A_RECEBER",
            origem_tipo="COMERCIALIZACAO",
            origem_id=comercializacao_b.id,
        ),
        Receita(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_id,
            plano_conta_id=plano_receita.id,
            descricao="Receita sem lote vinculado",
            valor_total=1000.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            status="A_RECEBER",
            origem_tipo="COMERCIALIZACAO",
            origem_id=comercializacao_sem_lote.id,
        ),
    ])

    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação com custo a ratear por lote",
        data_realizada=date.today(),
        custo_total=500.0,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.flush()
    execucao = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao.id,
        production_unit_id=pu.id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id,
        custo_real=500.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add(execucao)
    await session.flush()
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="OPERATION_EXECUTION",
        source_id=execucao.id,
        operation_execution_id=execucao.id,
        amount=500.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )
    await session.commit()

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(
        safra_id=safra.id,
        production_unit_id=pu.id,
    )

    assert dre.lotes_sem_vinculo == 1
    margens_por_id = {m.produto_colhido_id: m for m in dre.margem_por_lote}
    assert set(margens_por_id.keys()) == {lote_a.id, lote_b.id}
    # custo total rateado deve bater exatamente com o custo direto da PU, sem perda por arredondamento.
    assert round(sum(m.custo_rateado for m in dre.margem_por_lote), 2) == dre.custos_diretos
    assert margens_por_id[lote_a.id].custo_rateado == 300.0
    assert margens_por_id[lote_b.id].custo_rateado == 200.0
    assert margens_por_id[lote_a.id].margem == 5700.0
    assert margens_por_id[lote_b.id].margem == 3800.0
    assert any(w.codigo == "COMERCIALIZACAO_SEM_LOTE_VINCULADO" for w in dre.warnings)
