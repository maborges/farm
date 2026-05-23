from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import agricola.alertas.service as alertas_module
from agricola.alertas.service import AlertasAgricolasService
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from core.cadastros.produtos.models import Produto
from financeiro.models.despesa import Despesa
from financeiro.models.lancamento import LancamentoFinanceiro
from financeiro.models.plano_conta import PlanoConta
from operacional.models.compras import DevolucaoFornecedor, Fornecedor, ItemDevolucao, PedidoCompra
from operacional.models.estoque import EstoqueMovimento
from agricola.tarefas.models import SafraTarefa
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_cultivo,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
)
from test_operational_workflow_governance_step02 import _garantir_unidade_ha
from test_operational_workflow_governance_step05 import _criar_deposito, _criar_produto
from test_operational_workflow_governance_step07 import _criar_contexto_reconciliacao
from agricola.production_units.models import ProductionUnit


async def _criar_plano_conta(session: AsyncSession, tenant_id: uuid.UUID) -> PlanoConta:
    plano = PlanoConta(
        tenant_id=tenant_id,
        parent_id=None,
        codigo=f"8.10.{str(uuid.uuid4())[:8]}",
        nome="Plano Step10",
        tipo="DESPESA",
        natureza="ANALITICA",
        categoria_rfb="CUSTEIO",
        ordem=1,
        is_sistema=False,
        ativo=True,
    )
    session.add(plano)
    await session.flush()
    return plano


@pytest.mark.asyncio
async def test_step10_relatorio_lista_inconsistencias_e_sugestoes(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _criar_contexto_reconciliacao(session, tenant_id)
    plano = await _criar_plano_conta(session, tenant_id)

    tarefa = SafraTarefa(
        tenant_id=tenant_id,
        safra_id=safra.id,
        origem="MANUAL",
        tipo="PLANTIO",
        descricao="Tarefa legada",
        criticidade="NORMAL",
        prioridade="MEDIA",
        status="CONCLUIDA",
        obs=None,
    )
    session.add(tarefa)

    operacao_sem_exec = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação sem execução",
        data_realizada=date.today(),
        custo_total=120.0,
        custo_por_ha=2.0,
        status="REALIZADA",
    )
    session.add(operacao_sem_exec)

    operacao_reflexo = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PULVERIZACAO",
        descricao="Operação com reflexo faltante",
        data_realizada=date.today(),
        custo_total=150.0,
        custo_por_ha=3.0,
        status="REALIZADA",
    )
    session.add(operacao_reflexo)
    await session.flush()

    execucao_reflexo = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao_reflexo.id,
        production_unit_id=pu.id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id,
        custo_real=150.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add(execucao_reflexo)
    await session.flush()

    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="OPERATION_EXECUTION",
        source_id=execucao_reflexo.id,
        operation_execution_id=execucao_reflexo.id,
        amount=149.5,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )

    origem_dup = uuid.uuid4()
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="MANUAL",
        source_id=origem_dup,
        amount=40.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="MANUAL",
        source_id=origem_dup,
        amount=35.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )

    despesa_sem_origem = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano.id,
        descricao="Despesa automática sem origem",
        valor_total=80.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="OPERACAO_AGRICOLA",
        origem_id=None,
        ativo=True,
    )
    despesa_dup_a = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano.id,
        descricao="Despesa automática duplicada 1",
        valor_total=80.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="ABASTECIMENTO",
        origem_id=uuid.uuid4(),
        ativo=True,
    )
    despesa_dup_b = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano.id,
        descricao="Despesa automática duplicada 2",
        valor_total=80.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="ABASTECIMENTO",
        origem_id=despesa_dup_a.origem_id,
        ativo=True,
    )
    session.add_all([despesa_sem_origem, despesa_dup_a, despesa_dup_b])

    pedido = PedidoCompra(
        tenant_id=tenant_id,
        solicitacao_id=None,
        cotacao_id=None,
        fornecedor_nome="Fornecedor Legado",
        fornecedor_contato=None,
        item_id=produto.id,
        deposito_id=deposito.id,
        quantidade=10.0,
        unidade="UN",
        valor_unitario=10.0,
        valor_total=100.0,
        status="RECEBIDO",
        economia_absoluta=0.0,
        economia_percentual=0.0,
    )
    session.add(pedido)

    fornecedor = Fornecedor(
        tenant_id=tenant_id,
        nome_fantasia="Fornecedor Step10",
    )
    session.add(fornecedor)
    await session.flush()

    devolucao = DevolucaoFornecedor(
        tenant_id=tenant_id,
        pedido_id=pedido.id,
        fornecedor_id=fornecedor.id,
        data_devolucao=date.today(),
        motivo="OUTRO",
        status="CONCLUIDA",
        observacoes="Devolução legada",
    )
    session.add(devolucao)
    await session.flush()
    session.add(
        ItemDevolucao(
            devolucao_id=devolucao.id,
            produto_id=produto.id,
            deposito_origem_id=deposito.id,
            lote_id=None,
            quantidade=2.0,
            custo_unitario=10.0,
        )
    )

    movimento = EstoqueMovimento(
        tenant_id=tenant_id,
        data_movimento=date.today(),
        tipo_movimento="ENTRADA",
        produto_id=produto.id,
        deposito_id=deposito.id,
        lote_id=None,
        quantidade=10.0,
        unidade_medida_id=unidade_ha_id,
        custo_unitario=10.0,
        custo_total=100.0,
        origem="COMPRA",
        origem_id=uuid.uuid4(),
        observacoes="Movimento legado",
    )
    session.add(movimento)
    await session.flush()
    session.add(
        LancamentoFinanceiro(
            tenant_id=tenant_id,
            safra_id=safra.id,
            descricao="Reflexo financeiro legado",
            valor=100.0,
            data=date.today(),
            tipo="CUSTO",
            categoria="OPERACOES",
            origem="ESTOQUE",
            origem_id=movimento.id,
        )
    )
    await session.commit()

    report = await AlertasAgricolasService(session, tenant_id).gerar_relatorio_governanca()
    codigos = {item.codigo for item in report.itens}

    assert "TAREFA_CONCLUIDA_SEM_OPERACAO" in codigos
    assert "OPERACAO_REALIZADA_SEM_EXECUCAO" in codigos
    assert "OPERACAO_COM_CUSTO_SEM_ALLOCATION" in codigos
    assert "ALLOCATION_POTENCIALMENTE_DUPLICADA" in codigos
    assert "DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM" in codigos
    assert "DESPESA_AUTOMATICA_SEM_ORIGEM" in codigos
    assert "PEDIDO_RECEBIDO_SEM_MOVIMENTO_OU_LOTE" in codigos
    assert "DEVOLUCAO_SEM_MOVIMENTO_ORIGINAL" in codigos
    assert "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" in codigos
    assert "DIVERGENCIA_VALOR_OPERACIONAL_APROPRIADO" in codigos

    assert report.por_severidade["RISCO_CRITICO"] >= 4
    assert report.por_tipo["COMPRAS"] >= 2
    assert all(item.sugestao_correcao for item in report.itens)


@pytest.mark.asyncio
async def test_step10_relatorio_ignora_casos_validos_e_isola_tenant(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    _, area_a, safra_a, cultivo_a, pu_a, produto_a, deposito_a, unidade_ha_a = await _criar_contexto_reconciliacao(session, tenant_a)
    await _criar_contexto_reconciliacao(session, tenant_b)

    operacao = OperacaoAgricola(
        tenant_id=tenant_a,
        safra_id=safra_a.id,
        cultivo_id=cultivo_a,
        production_unit_id=pu_a.id,
        talhao_id=area_a,
        tipo="PLANTIO",
        descricao="Operação válida",
        data_realizada=date.today(),
        custo_total=100.0,
        custo_por_ha=2.0,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.flush()

    execucao = OperacaoExecucao(
        tenant_id=tenant_a,
        operacao_id=operacao.id,
        production_unit_id=pu_a.id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_a,
        custo_real=100.0,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add(execucao)
    await session.flush()

    await registrar_cost_allocation(
        session,
        tenant_id=tenant_a,
        production_unit_id=pu_a.id,
        source="OPERATION_EXECUTION",
        source_id=execucao.id,
        operation_execution_id=execucao.id,
        amount=100.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )
    await session.commit()

    report = await AlertasAgricolasService(session, tenant_a).gerar_relatorio_governanca()
    codigos = {item.codigo for item in report.itens}
    assert "OPERACAO_REALIZADA_SEM_EXECUCAO" not in codigos
    assert "OPERACAO_COM_CUSTO_SEM_ALLOCATION" not in codigos
    assert report.tenant_id == tenant_a
