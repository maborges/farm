from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.alertas.service import AlertasAgricolasService
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa
from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.produtos.models import Produto
from core.models.tenant_audit_log import TenantAuditLog
from operacional.models.apontamento import ApontamentoUso
from operacional.models.compras import PedidoCompra
from operacional.models.estoque import Deposito


async def _garantir_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": f"Tenant {str(tenant_id)[:8]}", "doc": str(tenant_id)[:11]},
    )
    await session.commit()


async def _criar_unidade_produtiva(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    unidade_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'UP Workflow', true, now(), now())"
        ),
        {"id": str(unidade_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()
    return unidade_id


async def _criar_area(session: AsyncSession, tenant_id: uuid.UUID, unidade_id: uuid.UUID) -> uuid.UUID:
    area_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :unidade_id, 'TALHAO', 'Talhão Workflow', 50.0, true, now(), now())"
        ),
        {"id": str(area_id), "tenant_id": str(tenant_id), "unidade_id": str(unidade_id)},
    )
    await session.commit()
    return area_id


async def _criar_safra(session: AsyncSession, tenant_id: uuid.UUID) -> Safra:
    safra = Safra(
        tenant_id=tenant_id,
        ano_safra=f"{date.today().year}/{date.today().year + 1}",
        cultura="SOJA",
        status="PLANEJADA",
    )
    session.add(safra)
    await session.commit()
    await session.refresh(safra)
    return safra


async def _criar_cultivo(session: AsyncSession, tenant_id: uuid.UUID, safra_id: uuid.UUID) -> uuid.UUID:
    cultivo_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cultivos (id, tenant_id, safra_id, cultura, status, consorciado, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :safra_id, 'SOJA', 'PLANEJADO', false, now(), now())"
        ),
        {"id": str(cultivo_id), "tenant_id": str(tenant_id), "safra_id": str(safra_id)},
    )
    await session.commit()
    return cultivo_id


async def _criar_production_unit(
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
        area_ha=50.0,
        status="ATIVA",
    )
    session.add(pu)
    await session.commit()
    await session.refresh(pu)
    return pu


async def _criar_produto(session: AsyncSession, tenant_id: uuid.UUID) -> Produto:
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome="Produto Workflow",
        tipo="INSUMO",
        unidade_medida="KG",
        preco_medio=0.0,
        ativo=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto


async def _criar_deposito(session: AsyncSession, tenant_id: uuid.UUID, unidade_id: uuid.UUID) -> Deposito:
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        nome="Depósito Workflow",
        tipo="GERAL",
        ativo=True,
    )
    session.add(deposito)
    await session.commit()
    await session.refresh(deposito)
    return deposito


async def _criar_equipamento(session: AsyncSession, tenant_id: uuid.UUID, unidade_id: uuid.UUID) -> Equipamento:
    equipamento = Equipamento(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        nome="Equipamento Workflow",
        tipo="TRATOR",
        combustivel="DIESEL",
        status="ATIVO",
        horimetro_atual=100.0,
        km_atual=200.0,
        ativo=True,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


@pytest.mark.asyncio
async def test_detector_ignora_tarefa_nao_operacional_sem_operacao(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)

    tarefa_operacional = SafraTarefa(
        tenant_id=tenant_id,
        safra_id=safra.id,
        origem="MANUAL",
        tipo="PLANTIO",
        descricao="Plantio sem operação",
        status="CONCLUIDA",
        criticidade="NORMAL",
        prioridade="MEDIA",
    )
    tarefa_administrativa = SafraTarefa(
        tenant_id=tenant_id,
        safra_id=safra.id,
        origem="MANUAL",
        tipo="ADMINISTRATIVA",
        descricao="Checklist administrativo",
        status="CONCLUIDA",
        criticidade="NORMAL",
        prioridade="MEDIA",
    )
    session.add_all([tarefa_operacional, tarefa_administrativa])
    await session.commit()

    svc = AlertasAgricolasService(session, tenant_id)
    findings = await svc.detectar_inconsistencias_operacionais()
    finding = next(item for item in findings if item.codigo == "TAREFA_CONCLUIDA_SEM_OPERACAO")

    assert finding.total == 1
    assert finding.severidade == "INCONSISTENCIA_MODERADA"
    assert str(tarefa_operacional.id) in finding.amostras
    assert str(tarefa_administrativa.id) not in finding.amostras


@pytest.mark.asyncio
async def test_detector_classifica_inconsistencias_operacionais(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    produto = await _criar_produto(session, tenant_id)
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    equipamento = await _criar_equipamento(session, tenant_id, unidade_id)

    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="PULVERIZACAO",
        descricao="Operação sem execução",
        data_realizada=date.today(),
        area_aplicada_ha=10.0,
        custo_total=500.0,
        custo_por_ha=50.0,
        status="REALIZADA",
    )
    apontamento = ApontamentoUso(
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        data=datetime.now(timezone.utc),
        turno="INTEGRAL",
        horimetro_inicio=10.0,
        horimetro_fim=12.0,
        unidade_produtiva_id=unidade_id,
        custo_total=320.0,
    )
    pedido = PedidoCompra(
        tenant_id=tenant_id,
        fornecedor_nome="Fornecedor Workflow",
        valor_total=2200.0,
        status="RECEBIDO",
    )
    allocation_source_id = uuid.uuid4()
    allocation_a = CostAllocation(
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="MANUAL",
        source_id=allocation_source_id,
        cost_category="OUTROS",
        amount=100.0,
        allocation_date=date.today(),
    )
    allocation_b = CostAllocation(
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="MANUAL",
        source_id=allocation_source_id,
        cost_category="OUTROS",
        amount=100.0,
        allocation_date=date.today(),
    )
    session.add_all([operacao, apontamento, pedido, allocation_a, allocation_b])
    await session.commit()

    svc = AlertasAgricolasService(session, tenant_id)
    findings = {item.codigo: item for item in await svc.detectar_inconsistencias_operacionais()}

    assert findings["OPERACAO_REALIZADA_SEM_EXECUCAO"].severidade == "INCONSISTENCIA_MODERADA"
    assert findings["OPERACAO_COM_CUSTO_SEM_ALLOCATION"].severidade == "RISCO_ECONOMICO"
    assert findings["APONTAMENTO_COM_CUSTO_SEM_CONTEXTO"].severidade == "RISCO_ECONOMICO"
    assert findings["PEDIDO_RECEBIDO_SEM_MOVIMENTO_OU_LOTE"].severidade == "RISCO_CRITICO"
    assert findings["ALLOCATION_POTENCIALMENTE_DUPLICADA"].severidade == "RISCO_CRITICO"


@pytest.mark.asyncio
async def test_verificar_governanca_registra_auditoria_e_notifica(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)

    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        production_unit_id=pu.id,
        talhao_id=area_id,
        tipo="ADUBACAO_NITROGENIO",
        descricao="Operação auditável",
        data_realizada=date.today(),
        area_aplicada_ha=8.0,
        custo_total=250.0,
        custo_por_ha=31.25,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.commit()

    svc = AlertasAgricolasService(session, tenant_id)
    svc.notif_svc.criar_sem_duplicar = AsyncMock(return_value=None)

    total = await svc.verificar_governanca_operacional()

    stmt = (
        select(TenantAuditLog)
        .where(
            TenantAuditLog.tenant_id == tenant_id,
            TenantAuditLog.resource == "operational_workflow_governance",
            TenantAuditLog.action == "scan",
        )
        .order_by(TenantAuditLog.created_at.desc())
    )
    audit_log = (await session.execute(stmt)).scalars().first()

    assert total >= 1
    assert svc.notif_svc.criar_sem_duplicar.await_count == total
    assert audit_log is not None
    assert audit_log.payload_after["total_findings"] == total
