"""Economic reconciliation of a stock movement already included in an operation."""

import uuid
from datetime import date

import pytest
from test_operational_workflow_governance_step07 import _criar_contexto_reconciliacao

from agricola.alertas.service import AlertasAgricolasService
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from operacional.services.estoque_ledger import registrar_ledger_estoque


@pytest.mark.asyncio
async def test_movimento_vinculado_a_allocation_de_execucao_nao_duplica_custo(session):
    tenant = uuid.uuid4()
    _, area, safra, cultivo, pu, produto, deposito, unidade = await _criar_contexto_reconciliacao(
        session, tenant
    )
    operacao = OperacaoAgricola(
        tenant_id=tenant,
        safra_id=safra.id,
        cultivo_id=cultivo,
        production_unit_id=pu.id,
        talhao_id=area,
        tipo="ADUBAÇÃO",
        descricao="Consumo de fertilizante",
        data_realizada=date.today(),
        custo_total=100,
        custo_por_ha=100,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.flush()
    execucao = OperacaoExecucao(
        tenant_id=tenant,
        operacao_id=operacao.id,
        production_unit_id=pu.id,
        data_execucao=date.today(),
        quantidade_executada=1,
        quantidade_devolvida=0,
        unidade_medida_id=unidade,
        custo_real=100,
        status="REALIZADA",
    )
    session.add(execucao)
    await session.flush()
    movimento = await registrar_ledger_estoque(
        session,
        tenant_id=tenant,
        produto_id=produto.id,
        deposito_id=deposito.id,
        tipo_movimento="SAIDA",
        quantidade=10,
        custo_unitario=10,
        origem="OPERACAO_EXECUCAO",
        origem_id=execucao.id,
        operacao_execucao_id=execucao.id,
        production_unit_id=pu.id,
    )
    await session.flush()
    allocation = await registrar_cost_allocation(
        session,
        tenant_id=tenant,
        production_unit_id=pu.id,
        source="OPERATION_EXECUTION",
        source_id=execucao.id,
        operation_execution_id=execucao.id,
        inventory_movement_id=movimento.id,
        cost_category="OUTROS",
        amount=100,
        allocation_date=date.today(),
        allocation_method="DIRECT",
    )
    await session.flush()
    svc = AlertasAgricolasService(session, tenant)
    assert await svc._detectar_divergencia_valor_operacional_apropriado() is None
    allocation.amount = 90
    await session.flush()
    finding = await svc._detectar_divergencia_valor_operacional_apropriado()
    assert finding is not None
    assert finding.meta["movimentos_divergentes"] == 1
