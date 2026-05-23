from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select
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
from financeiro.models.despesa import Despesa
from financeiro.models.lancamento import LancamentoFinanceiro
from financeiro.models.plano_conta import PlanoConta
from financeiro.models.rateio import Rateio
from notificacoes.models import Notificacao
from operacional.services.estoque_ledger import registrar_ledger_estoque
from test_operational_workflow_governance_step02 import _garantir_unidade_ha
from test_operational_workflow_governance_step03 import _criar_area, _criar_cultivo, _criar_safra, _criar_unidade_produtiva, _garantir_tenant
from test_operational_workflow_governance_step05 import _criar_deposito, _criar_produto
from test_operational_workflow_governance_step07 import _criar_contexto_reconciliacao


async def _criar_plano_conta(session: AsyncSession, tenant_id: uuid.UUID) -> PlanoConta:
    plano = PlanoConta(
        tenant_id=tenant_id,
        parent_id=None,
        codigo=f"8.08.{str(uuid.uuid4())[:8]}",
        nome="Plano Governança",
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
async def test_step08_detecta_cost_allocation_duplicado_mesma_origem(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    _, _, _, _, pu, _, _, _ = await _criar_contexto_reconciliacao(session, tenant_id)
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
    assert any(f.codigo == "ALLOCATION_POTENCIALMENTE_DUPLICADA" for f in findings)


@pytest.mark.asyncio
async def test_step08_detecta_despesa_automatica_duplicada_mesma_origem(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    plano = await _criar_plano_conta(session, tenant_id)
    origem_id = uuid.uuid4()

    despesas = [
        Despesa(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_id,
            plano_conta_id=plano.id,
            descricao="Despesa automática 1",
            valor_total=100.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            status="PAGO",
            origem_tipo="OPERACAO_AGRICOLA",
            origem_id=origem_id,
            ativo=True,
        ),
        Despesa(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_id,
            plano_conta_id=plano.id,
            descricao="Despesa automática 2",
            valor_total=100.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            status="PAGO",
            origem_tipo="OPERACAO_AGRICOLA",
            origem_id=origem_id,
            ativo=True,
        ),
    ]
    session.add_all(despesas)
    await session.commit()

    findings = await AlertasAgricolasService(session, tenant_id).detectar_inconsistencias_reconciliacao_economica()
    assert any(f.codigo == "DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM" for f in findings)


@pytest.mark.asyncio
async def test_step08_detecta_movimento_com_custo_sem_allocation(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    _, _, safra, _, _, produto, deposito, _ = await _criar_contexto_reconciliacao(session, tenant_id)

    mov = await registrar_ledger_estoque(
        session,
        tenant_id=tenant_id,
        produto_id=produto.id,
        deposito_id=deposito.id,
        lote_id=None,
        tipo_movimento="ENTRADA",
        quantidade=4.0,
        custo_unitario=25.0,
        origem="COMPRA",
        origem_id=uuid.uuid4(),
        observacoes="Recebimento sem allocation",
    )
    await session.flush()
    session.add(
        LancamentoFinanceiro(
            tenant_id=tenant_id,
            safra_id=safra.id,
            descricao="Reflexo financeiro do movimento",
            valor=100.0,
            data=date.today(),
            tipo="CUSTO",
            categoria="OPERACOES",
            origem="ESTOQUE",
            origem_id=mov.id,
        )
    )
    await session.commit()

    findings = await AlertasAgricolasService(session, tenant_id).detectar_inconsistencias_reconciliacao_economica()
    assert any(f.codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" for f in findings)


@pytest.mark.asyncio
async def test_step08_detecta_divergencia_valor_operacional_apropriado(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
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
        descricao="Operação com divergência",
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
        amount=90.0,
        allocation_date=date.today(),
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )
    await session.commit()

    findings = await AlertasAgricolasService(session, tenant_id).detectar_inconsistencias_reconciliacao_economica()
    assert any(f.codigo == "DIVERGENCIA_VALOR_OPERACIONAL_APROPRIADO" for f in findings)


@pytest.mark.asyncio
async def test_step08_rateio_financeiro_legitimo_nao_gera_falso_positivo(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    unidade_id, _, _, _, pu, _, _, _ = await _criar_contexto_reconciliacao(session, tenant_id)
    plano = await _criar_plano_conta(session, tenant_id)
    despesa = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano.id,
        descricao="Despesa rateada",
        valor_total=500.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="PAGO",
        origem_tipo="FIN_RATEIO",
        origem_id=None,
        ativo=True,
    )
    session.add(despesa)
    await session.flush()

    rateio = Rateio(
        tenant_id=tenant_id,
        despesa_id=despesa.id,
        safra_id=None,
        talhao_id=None,
        valor_rateado=200.0,
        percentual=40.0,
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
        amount=200.0,
        allocation_date=date.today(),
        cost_category="DESPESA_FINANCEIRA",
        allocation_method="DIRECT",
    )
    await session.commit()

    findings = await AlertasAgricolasService(session, tenant_id).detectar_inconsistencias_reconciliacao_economica()
    assert findings == []
