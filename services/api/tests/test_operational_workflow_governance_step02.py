from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.operacoes.schemas import OperacaoAgricolaUpdate
from agricola.operacoes.service import OperacaoService
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa
from agricola.tarefas.service import TarefaService
from core.models.tenant_audit_log import TenantAuditLog
from notificacoes.models import Notificacao


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
            "VALUES (:id, :tenant_id, 'UP Step02', true, now(), now())"
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
            "VALUES (:id, :tenant_id, :unidade_id, 'TALHAO', 'Talhão Step02', 40.0, true, now(), now())"
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
        area_ha=40.0,
        status="ATIVA",
    )
    session.add(pu)
    await session.commit()
    await session.refresh(pu)
    return pu


async def _garantir_unidade_ha(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    existente = (
        await session.execute(
            text(
                "SELECT id FROM unidades_medida "
                "WHERE ativo = true AND codigo = 'HA' AND tenant_id IS NULL "
                "LIMIT 1"
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        return existente

    unidade_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_medida "
            "(id, tenant_id, codigo, nome, dimensao, codigo_canonico, fator_canonico, sistema, ativo, casas_decimais, eh_canonica, created_at, updated_at) "
            "VALUES (:id, NULL, 'HA', 'Hectare', 'AREA', 'HA', 1, true, true, 4, true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(unidade_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()
    return unidade_id


async def _criar_tarefa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    *,
    tipo: str,
    obs: str | None = None,
) -> SafraTarefa:
    tarefa = SafraTarefa(
        tenant_id=tenant_id,
        safra_id=safra_id,
        origem="MANUAL",
        tipo=tipo,
        descricao=f"Tarefa {tipo}",
        criticidade="NORMAL",
        prioridade="MEDIA",
        status="EM_EXECUCAO",
        obs=obs,
    )
    session.add(tarefa)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


async def _criar_operacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    cultivo_id: uuid.UUID,
    area_id: uuid.UUID,
    *,
    production_unit_id: uuid.UUID | None,
    status: str = "PLANEJADA",
    custo_total: float = 500.0,
) -> OperacaoAgricola:
    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        production_unit_id=production_unit_id,
        talhao_id=area_id,
        tipo="PULVERIZACAO",
        descricao="Operação Step02",
        data_realizada=date.today(),
        area_aplicada_ha=10.0,
        custo_total=custo_total,
        custo_por_ha=50.0 if custo_total else 0.0,
        status=status,
    )
    session.add(operacao)
    await session.commit()
    await session.refresh(operacao)
    return operacao


@pytest.mark.asyncio
async def test_tarefa_operacional_sem_operacao_com_justificativa_audita_sem_warning(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(
        session,
        tenant_id,
        safra.id,
        tipo="PLANTIO",
        obs="Fechamento administrativo por intempérie e reprogramação em operação futura.",
    )

    svc = TarefaService(session, tenant_id)
    await svc.concluir(tarefa.id)
    await session.commit()

    notif = (
        await session.execute(
            select(Notificacao).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
            )
        )
    ).scalars().first()
    audit = (
        await session.execute(
            select(TenantAuditLog).where(
                TenantAuditLog.tenant_id == tenant_id,
                TenantAuditLog.resource == "operational_workflow_governance",
                TenantAuditLog.action == "manual_close_just",
            )
        )
    ).scalars().first()

    assert notif is None
    assert audit is not None


@pytest.mark.asyncio
async def test_tarefa_operacional_sem_operacao_sem_justificativa_gera_warning(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(session, tenant_id, safra.id, tipo="PLANTIO")

    svc = TarefaService(session, tenant_id)
    await svc.concluir(tarefa.id)
    await session.commit()

    notif = (
        await session.execute(
            select(Notificacao).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
                Notificacao.origem_id == f"tarefa:{tarefa.id}:manual_closure_without_operation",
            )
        )
    ).scalars().first()

    assert notif is not None
    assert notif.nivel == "WARNING"


@pytest.mark.asyncio
async def test_tarefa_administrativa_fecha_sem_falso_positivo(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(session, tenant_id, safra.id, tipo="ADMINISTRATIVA")

    svc = TarefaService(session, tenant_id)
    await svc.concluir(tarefa.id)
    await session.commit()

    total_notifs = (
        await session.execute(
            select(func.count(Notificacao.id)).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
            )
        )
    ).scalar_one()
    assert total_notifs == 0


@pytest.mark.asyncio
async def test_operacao_realizada_com_custo_e_allocation_correto(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await _garantir_unidade_ha(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operacao = await _criar_operacao(
        session,
        tenant_id,
        safra.id,
        cultivo_id,
        area_id,
        production_unit_id=pu.id,
    )

    svc = OperacaoService(session, tenant_id)
    await svc.atualizar(operacao.id, OperacaoAgricolaUpdate(status="REALIZADA"))
    await session.commit()

    execucao = (
        await session.execute(select(OperacaoExecucao).where(OperacaoExecucao.operacao_id == operacao.id))
    ).scalars().first()
    allocations = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.operation_execution_id == execucao.id,
            )
        )
    ).scalars().all()

    assert execucao is not None
    assert len(allocations) == 1


@pytest.mark.asyncio
async def test_operacao_realizada_com_custo_sem_allocation_gera_warning(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await _garantir_unidade_ha(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    operacao = await _criar_operacao(
        session,
        tenant_id,
        safra.id,
        cultivo_id,
        area_id,
        production_unit_id=None,
    )

    svc = OperacaoService(session, tenant_id)
    await svc.atualizar(operacao.id, OperacaoAgricolaUpdate(status="REALIZADA"))
    await session.commit()

    notif = (
        await session.execute(
            select(Notificacao).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
                Notificacao.origem_id == f"operacao:{operacao.id}:missing_allocation_context",
            )
        )
    ).scalars().first()
    allocations = (
        await session.execute(select(func.count(CostAllocation.id)).where(CostAllocation.tenant_id == tenant_id))
    ).scalar_one()

    assert notif is not None
    assert allocations == 0


@pytest.mark.asyncio
async def test_nao_duplica_cost_allocation_existente(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await _garantir_unidade_ha(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operacao = await _criar_operacao(
        session,
        tenant_id,
        safra.id,
        cultivo_id,
        area_id,
        production_unit_id=pu.id,
        status="REALIZADA",
    )
    execucao = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao.id,
        production_unit_id=pu.id,
        data_execucao=date.today(),
        quantidade_executada=10.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=await _garantir_unidade_ha(session, tenant_id),
        custo_real=500.0,
        area_ha_executada=10.0,
        status="REALIZADA",
    )
    session.add(execucao)
    await session.flush()
    allocation = CostAllocation(
        tenant_id=tenant_id,
        production_unit_id=pu.id,
        source="OPERATION_EXECUTION",
        source_id=execucao.id,
        operation_execution_id=execucao.id,
        cost_category="OUTROS",
        amount=500.0,
        allocation_date=date.today(),
        allocation_method="DIRECT",
        allocation_basis=10.0,
    )
    session.add(allocation)
    await session.commit()

    svc = OperacaoService(session, tenant_id)
    await svc.atualizar(operacao.id, OperacaoAgricolaUpdate(custo_total=650.0))
    await session.commit()

    total_allocations = (
        await session.execute(
            select(func.count(CostAllocation.id)).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.operation_execution_id == execucao.id,
            )
        )
    ).scalar_one()
    assert total_allocations == 1
