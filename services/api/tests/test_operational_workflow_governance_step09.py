from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import agricola.alertas.service as alertas_module
import agricola.operacoes.service as operacoes_module
from agricola.alertas.service import AlertasAgricolasService
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.operacoes.schemas import OperacaoAgricolaUpdate
from agricola.operacoes.service import OperacaoService
from core.exceptions import BusinessRuleError
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from financeiro.schemas.despesa_schema import DespesaUpdate
from financeiro.services.despesa_service import DespesaService
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_cultivo,
    _criar_operacao,
    _criar_plano_custeio,
    _criar_production_unit,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
    _garantir_unidade_ha,
)
from test_operational_workflow_governance_step07 import _criar_contexto_reconciliacao


async def _criar_plano_conta(session: AsyncSession, tenant_id: uuid.UUID) -> PlanoConta:
    plano = PlanoConta(
        tenant_id=tenant_id,
        parent_id=None,
        codigo=f"8.09.{str(uuid.uuid4())[:8]}",
        nome="Plano Step09",
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
async def test_step09_bloqueia_cost_allocation_duplicado_novo_fluxo(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_ECONOMIC_AND_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    _, area_id, safra, cultivo_id, pu, _, _, unidade_ha_id = await _criar_contexto_reconciliacao(session, tenant_id)
    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação base",
        data_realizada=date.today(),
        custo_total=50.0,
        custo_por_ha=1.0,
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
        custo_real=50.0,
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
        amount=50.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )

    with pytest.raises(BusinessRuleError, match="Nao e possivel registrar cost allocation duplicada"):
        await registrar_cost_allocation(
            session,
            tenant_id=tenant_id,
            production_unit_id=pu.id,
            source="OPERATION_EXECUTION",
            source_id=execucao.id,
            operation_execution_id=execucao.id,
            amount=25.0,
            allocation_date=date.today(),
            cost_category="OUTROS",
            allocation_method="DIRECT",
        )


@pytest.mark.asyncio
async def test_step09_bloqueia_despesa_automatica_duplicada(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    plano = await _criar_plano_conta(session, tenant_id)
    origem_id = uuid.uuid4()

    despesa_a = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano.id,
        descricao="Despesa automática 1",
        valor_total=100.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="ABASTECIMENTO",
        origem_id=origem_id,
        ativo=True,
    )
    despesa_b = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano.id,
        descricao="Despesa automática 2",
        valor_total=100.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="ABASTECIMENTO",
        origem_id=origem_id,
        ativo=True,
    )
    session.add_all([despesa_a, despesa_b])
    await session.flush()

    with pytest.raises(BusinessRuleError, match="Nao e possivel registrar despesa automatica duplicada"):
        await AlertasAgricolasService(session, tenant_id).validar_despesa_automatica_unica_origem(
            despesa_b,
            allow_block=True,
        )


@pytest.mark.asyncio
async def test_step09_operacao_com_custo_sem_allocation_bloqueia(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_ECONOMIC_AND_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await _garantir_unidade_ha(session)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operacao_id = await _criar_operacao(session, tenant_id, safra.id, cultivo_id, area_id, production_unit_id=pu.id)

    async def _falhar_alloc(*args, **kwargs):
        raise Exception("allocation failed")

    monkeypatch.setattr(operacoes_module, "registrar_cost_allocation", _falhar_alloc)

    with pytest.raises(BusinessRuleError, match="Nao e possivel concluir a operacao com custo sem apropriacao economica"):
        await OperacaoService(session, tenant_id).atualizar(operacao_id, OperacaoAgricolaUpdate(status="REALIZADA"))

    await session.rollback()


@pytest.mark.asyncio
async def test_step09_divergencia_pequena_fica_em_warning(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    _, area_id, safra, cultivo_id, pu, _, _, unidade_ha_id = await _criar_contexto_reconciliacao(session, tenant_id)

    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação com divergência pequena",
        data_realizada=date.today(),
        custo_total=100.0,
        custo_por_ha=2.0,
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
        custo_real=100.0,
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
        amount=99.5,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await session.commit()

    findings = await AlertasAgricolasService(session, tenant_id).detectar_inconsistencias_reconciliacao_economica()
    finding = next(f for f in findings if f.codigo == "DIVERGENCIA_VALOR_OPERACIONAL_APROPRIADO")
    assert finding.severidade == "WARNING_LEVE"


@pytest.mark.asyncio
async def test_step09_legado_historico_nao_bloqueia_edicao_corretiva(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_ECONOMIC_AND_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    plano = await _criar_plano_conta(session, tenant_id)

    despesa = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano.id,
        descricao="Legado para correção",
        valor_total=200.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="ABASTECIMENTO",
        origem_id=uuid.uuid4(),
        ativo=True,
    )
    session.add(despesa)
    await session.commit()

    atualizado = await DespesaService(session, tenant_id).atualizar(
        despesa.id,
        DespesaUpdate(descricao="Legado corrigido sem bloqueio"),
    )
    await session.commit()

    assert atualizado.descricao == "Legado corrigido sem bloqueio"
