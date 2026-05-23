from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import agricola.alertas.service as alertas_module
from agricola.alertas.service import AlertasAgricolasService
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from core.cadastros.produtos.models import Produto
from core.models.tenant_audit_log import TenantAuditLog
from notificacoes.models import Notificacao
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import Deposito
from operacional.services.estoque_ledger import registrar_ledger_estoque
from test_operational_workflow_governance_step03 import _criar_area, _criar_cultivo, _criar_safra, _criar_unidade_produtiva, _garantir_tenant
from test_operational_workflow_governance_step02 import _criar_production_unit, _garantir_unidade_ha
from test_operational_workflow_governance_step05 import _criar_deposito, _criar_produto


async def _criar_contexto_reconciliacao(session: AsyncSession, tenant_id: uuid.UUID):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    produto = await _criar_produto(session, tenant_id)
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    unidade_ha_id = await _garantir_unidade_ha(session, tenant_id)
    return unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id


@pytest.mark.asyncio
async def test_reconciliacao_detecta_custo_operacional_sem_reflexo_economico(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _criar_contexto_reconciliacao(session, tenant_id)

    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação base",
        data_realizada=date.today(),
        custo_total=125.0,
        custo_por_ha=2.5,
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
        custo_real=125.0,
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
        cost_category="OUTROS",
        amount=125.0,
        allocation_date=date.today(),
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )
    await session.commit()

    svc = AlertasAgricolasService(session, tenant_id)
    total = await svc.verificar_reconciliacao_economica()

    assert total == 1

    notificacao = (
        await session.execute(
            select(Notificacao).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
                Notificacao.origem_id == "CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO",
            )
        )
    ).scalars().first()
    assert notificacao is not None

    auditorias = (
        await session.execute(
            select(TenantAuditLog).where(
                TenantAuditLog.tenant_id == tenant_id,
                TenantAuditLog.resource == "operational_workflow_governance",
                TenantAuditLog.action == "reconcile",
            )
        )
    ).scalars().all()
    assert auditorias


@pytest.mark.asyncio
async def test_reconciliacao_nao_cria_falso_positivo_para_lancamento_estoque_legitimo(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _criar_contexto_reconciliacao(session, tenant_id)

    mov = await registrar_ledger_estoque(
        session,
        tenant_id=tenant_id,
        produto_id=produto.id,
        deposito_id=deposito.id,
        lote_id=None,
        tipo_movimento="SAIDA",
        quantidade=2.0,
        custo_unitario=8.0,
        origem="ESTOQUE",
        origem_id=uuid.uuid4(),
        observacoes="Movimento legítimo",
    )
    await session.flush()
    session.add(
        LancamentoFinanceiro(
            tenant_id=tenant_id,
            safra_id=safra.id,
            descricao="Uso de insumo legítimo",
            valor=16.0,
            data=date.today(),
            tipo="CUSTO",
            categoria="INSUMOS",
            origem="ESTOQUE",
            origem_id=mov.id,
        )
    )
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="INVENTORY_MOVEMENT",
        source_id=mov.id,
        inventory_movement_id=mov.id,
        cost_category="OUTROS",
        amount=16.0,
        allocation_date=date.today(),
        allocation_method="DIRECT",
        allocation_basis=2.0,
    )
    await session.commit()

    total = await AlertasAgricolasService(session, tenant_id).verificar_reconciliacao_economica()
    assert total == 0


@pytest.mark.asyncio
async def test_reconciliacao_detecta_allocations_duplicadas(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _criar_contexto_reconciliacao(session, tenant_id)

    origem_id = uuid.uuid4()

    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="MANUAL",
        source_id=origem_id,
        amount=30.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="MANUAL",
        source_id=origem_id,
        amount=45.0,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
    )
    await session.commit()

    findings = await AlertasAgricolasService(session, tenant_id).detectar_inconsistencias_operacionais()
    codigos = {finding.codigo for finding in findings}
    assert "ALLOCATION_POTENCIALMENTE_DUPLICADA" in codigos
