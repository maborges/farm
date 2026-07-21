from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import agricola.alertas.service as alertas_module
from agricola.alertas.service import AlertasAgricolasService
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoExecucao
from agricola.operacoes.schemas import OperacaoAgricolaUpdate
from agricola.operacoes.service import OperacaoService
from agricola.tarefas.service import TarefaService
from core.exceptions import BusinessRuleError
from core.models.tenant_audit_log import TenantAuditLog
from financeiro.models.despesa import Despesa
from financeiro.schemas.despesa_schema import DespesaUpdate
from financeiro.services.despesa_service import DespesaService
from notificacoes.models import Notificacao
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_cultivo,
    _criar_operacao,
    _criar_plano_custeio,
    _criar_production_unit,
    _criar_safra,
    _criar_tarefa,
    _criar_unidade_produtiva,
    _garantir_tenant,
    _garantir_unidade_ha,
)


@pytest.mark.asyncio
async def test_warning_only_nao_bloqueia_risco_economico_novo(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await _garantir_unidade_ha(session)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    operacao_id = await _criar_operacao(session, tenant_id, safra.id, cultivo_id, area_id, production_unit_id=None)

    # SOIL-PLAN-EXEC-04K: o bloqueio de "operação REALIZADA com custo sem
    # ProductionUnit/CostAllocation" é direcionado e não depende do modo global
    # de enforcement — mesmo em WARNING_ONLY (que continua não bloqueando os
    # demais alertas), esse caminho específico levanta BusinessRuleError.
    with pytest.raises(BusinessRuleError):
        await OperacaoService(session, tenant_id).atualizar(operacao_id, OperacaoAgricolaUpdate(status="REALIZADA"))


@pytest.mark.asyncio
async def test_block_critical_bloqueia_despesa_automatica_sem_origem(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    plano_id = await _criar_plano_custeio(session, tenant_id)

    despesa = Despesa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_id,
        descricao="Despesa automatica sem origem",
        valor_total=150.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        data_pagamento=date.today(),
        status="PAGO",
        origem_tipo="OPERACAO_AGRICOLA",
        origem_id=None,
    )
    session.add(despesa)
    await session.flush()

    with pytest.raises(BusinessRuleError, match="Nao e possivel registrar despesa automatica sem origem rastreavel"):
        await AlertasAgricolasService(session, tenant_id).validar_despesa_origem_leve(
            despesa,
            allow_block=True,
        )

    await session.rollback()


@pytest.mark.asyncio
async def test_tarefa_administrativa_nao_bloqueia_em_block_critical(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(session, tenant_id, safra.id, tipo="ADMINISTRATIVA")

    await TarefaService(session, tenant_id).concluir(tarefa.id)
    await session.commit()

    total = (
        await session.execute(
            select(func.count(Notificacao.id)).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
            )
        )
    ).scalar_one()
    assert total == 0


@pytest.mark.asyncio
async def test_operacao_com_allocation_ok_passa_em_modo_economico(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
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

    await OperacaoService(session, tenant_id).atualizar(operacao_id, OperacaoAgricolaUpdate(status="REALIZADA"))
    await session.commit()

    execucao = (
        await session.execute(select(OperacaoExecucao).where(OperacaoExecucao.operacao_id == operacao_id))
    ).scalars().first()
    allocation = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.operation_execution_id == execucao.id,
            )
        )
    ).scalars().first()

    assert execucao is not None
    assert allocation is not None


@pytest.mark.asyncio
async def test_operacao_sem_allocation_bloqueia_em_modo_economico(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
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
    operacao_id = await _criar_operacao(session, tenant_id, safra.id, cultivo_id, area_id, production_unit_id=None)

    with pytest.raises(BusinessRuleError, match="Nao e possivel concluir a operacao com custo sem apropriacao economica"):
        await OperacaoService(session, tenant_id).atualizar(operacao_id, OperacaoAgricolaUpdate(status="REALIZADA"))

    await session.rollback()


@pytest.mark.asyncio
async def test_legado_historico_nao_bloqueia_edicao_corretiva(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    plano_id = await _criar_plano_custeio(session, tenant_id)

    despesa = Despesa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_id,
        descricao="Legado sem origem",
        valor_total=200.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        data_pagamento=date.today(),
        status="PAGO",
        origem_tipo="OPERACAO_AGRICOLA",
        origem_id=None,
    )
    session.add(despesa)
    await session.commit()

    atualizado = await DespesaService(session, tenant_id).atualizar(
        despesa.id,
        DespesaUpdate(descricao="Legado corrigido sem bloqueio"),
    )
    await session.commit()

    assert atualizado.descricao == "Legado corrigido sem bloqueio"


@pytest.mark.asyncio
async def test_justificativa_permanece_aceita_para_warning_moderado(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_ECONOMIC_AND_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(
        session,
        tenant_id,
        safra.id,
        tipo="PLANTIO",
        obs="Fechamento manual por replanejamento operacional",
    )

    await TarefaService(session, tenant_id).concluir(tarefa.id)
    await session.commit()

    audit = (
        await session.execute(
            select(TenantAuditLog).where(
                TenantAuditLog.tenant_id == tenant_id,
                TenantAuditLog.action == "manual_close_just",
            )
        )
    ).scalars().first()

    assert audit is not None
