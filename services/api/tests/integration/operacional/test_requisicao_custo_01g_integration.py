"""Certificação PostgreSQL real da apropriação econômica 01G."""

from __future__ import annotations

import asyncio
import os
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agricola.custos.material_consumption_service import MaterialConsumptionCostService
from agricola.custos.models import CostAllocation
from agricola.dashboard.service import DashboardAgricolaService
from agricola.dre.service import DREAgricolaV1Service
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from core.measurements.models import UnidadeMedida
from events.outbox_relay import DomainEventOutboxRelay
from events.outbox_service import DomainEventOutboxService
from operacional.models.estoque import RequisicaoMaterial, SaldoEstoque
from operacional.schemas.estoque import DestinacaoRequisicaoRequest
from operacional.services.requisicao_posse_service import RequisicaoPosseService
from tests.integration.operacional.test_requisicao_posse_01f1_integration import (
    _cleanup,
    _context,
    _create_operation,
    _create_request,
    _deliver,
    _identity,
    _prewarm_real_engine,
    _receive,
    _tenant_context,
)

pytestmark = pytest.mark.skipif(
    os.getenv("DEEPFARMS_RUN_REAL_01G") != "1",
    reason="certificação PostgreSQL real 01G opt-in",
)


def _engine():
    return create_async_engine(
        os.environ["DATABASE_URL"],
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=False,
        connect_args={"timeout": 30, "ssl": False, "server_settings": {"search_path": "farms"}},
    )


async def _context_with_production_unit(session):
    context = await _context(session)
    operation = (
        await session.execute(
            select(OperacaoAgricola).where(
                OperacaoAgricola.tenant_id == context[0],
                OperacaoAgricola.production_unit_id.is_not(None),
            ).limit(1)
        )
    ).scalars().first()
    if operation is None:
        pytest.skip("não há operação com ProductionUnit para certificar o 01G")
    return (
        *context[:6],
        operation.id,
        operation.safra_id,
        operation.talhao_id,
        operation.cultivo_id,
        operation.production_unit_id,
        operation.tipo,
    )


async def _restore_cost_average(factory, context):
    async with factory() as session:
        await _tenant_context(session, context[0])
        balance = await session.get(SaldoEstoque, context[5], with_for_update=True)
        balance.custo_medio = context[14]
        await session.commit()


@pytest.mark.asyncio
async def test_consumo_real_gera_cost_allocation_idempotente_e_dre():
    engine = _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    request_ids, operation_ids = [], []
    identity = None
    context = None
    try:
        await _prewarm_real_engine(engine)
        async with factory() as session:
            context = await _context_with_production_unit(session)
            await _tenant_context(session, context[0])
            balance = await session.get(SaldoEstoque, context[5], with_for_update=True)
            context = (
                *context,
                float(balance.quantidade_atual),
                float(balance.quantidade_reservada),
                balance.custo_medio,
            )
            balance.quantidade_atual = 100
            balance.custo_medio = 5
            person_id, identity = await _identity(session, context[0], context[1])
            operation_id = await _create_operation(session, context, "custo-real")
            operation_ids.append(operation_id)
            request_id, item_id = await _create_request(
                session, context, person_id, 100, "CONSUMIVEL", operation_id
            )
            request_ids.append(request_id)
            unit_id = (
                await session.execute(
                    select(UnidadeMedida.id).where(UnidadeMedida.ativo.is_(True)).limit(1)
                )
            ).scalar_one()
            execution = OperacaoExecucao(
                tenant_id=context[0],
                operacao_id=operation_id,
                production_unit_id=context[10],
                data_execucao=date.today(),
                quantidade_executada=1,
                quantidade_devolvida=0,
                unidade_medida_id=unit_id,
                status="REALIZADA",
            )
            session.add(execution)
            await session.flush()
            execution_id = execution.id
            await session.commit()

        delivery_id, _ = await _deliver(factory, context, request_id, item_id, context[1], 100)
        device_id, _ = await _receive(
            factory, context, request_id, item_id, delivery_id, context[1], 100
        )

        async with factory() as session:
            await _tenant_context(session, context[0])
            request = await session.get(RequisicaoMaterial, request_id)
            result = await RequisicaoPosseService(session, context[0]).destinar(
                request_id,
                DestinacaoRequisicaoRequest(
                    item_id=item_id,
                    entrega_evento_id=delivery_id,
                    tipo_evento="CONSUMO",
                    quantidade=80,
                    base_version=request.version,
                    client_operation_id=f"01G-CONSUME-{request_id}",
                    dispositivo_id=device_id,
                    operacao_execucao_id=execution_id,
                ),
                usuario_id=context[1],
                dispositivo_id=device_id,
            )
            event_id = result.evento_id
            await session.commit()

        async def process_worker():
            async with factory() as worker_session:
                await _tenant_context(worker_session, context[0])
                allocation = await MaterialConsumptionCostService(
                    worker_session, context[0]
                ).process(event_id)
                await worker_session.commit()
                return allocation.id

        worker_ids = await asyncio.gather(process_worker(), process_worker())
        assert worker_ids[0] == worker_ids[1]

        async with factory() as session:
            await _tenant_context(session, context[0])
            relay = DomainEventOutboxRelay(
                session,
                service=DomainEventOutboxService(session, context[0]),
            )
            relay_result = await relay.run_once(
                tenant_id=context[0],
                event_type="operational.material_request.consumo",
            )
            assert relay_result.processed == 1
            allocation = (
                await session.execute(
                    select(CostAllocation).where(
                        CostAllocation.tenant_id == context[0],
                        CostAllocation.requisicao_item_evento_id == event_id,
                    )
                )
            ).scalars().one()
            assert allocation.amount == 400
            assert allocation.operation_execution_id == execution_id
            assert allocation.cost_category == "INSUMO"
            assert allocation.source == "REQUISICAO_CONSUMO"
            assert allocation.allocation_basis == 80

            # O relay faz commit e encerra o SET LOCAL do tenant; a repetição
            # idempotente inicia uma nova transação no mesmo runner.
            await _tenant_context(session, context[0])
            same = await MaterialConsumptionCostService(session, context[0]).process(event_id)
            assert same.id == allocation.id
            assert (
                await session.scalar(
                    select(CostAllocation.id).where(
                        CostAllocation.tenant_id == context[0],
                        CostAllocation.requisicao_item_evento_id == event_id,
                    )
                )
                == allocation.id
            )

            dre = await DREAgricolaV1Service(session, context[0]).gerar(
                production_unit_id=context[10]
            )
            assert dre.custos_operacionais_detalhe.fontes.get("REQUISICAO_CONSUMO") == 400
            dashboard = await DashboardAgricolaService(
                session, context[0]
            ).resumo_financeiro_safra(context[7])
            assert dashboard.financeiro.custo_operacoes_total >= 400
            await session.rollback()
    finally:
        if context is not None:
            await _restore_cost_average(factory, context)
            await _cleanup(factory, context, request_ids, operation_ids, identity)
        await engine.dispose()


@pytest.mark.asyncio
async def test_consumos_parciais_distintos_acumulam_sem_duplicar_custo():
    engine = _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    request_ids, operation_ids = [], []
    identity = None
    context = None
    try:
        await _prewarm_real_engine(engine)
        async with factory() as session:
            context = await _context_with_production_unit(session)
            await _tenant_context(session, context[0])
            balance = await session.get(SaldoEstoque, context[5], with_for_update=True)
            context = (
                *context,
                float(balance.quantidade_atual),
                float(balance.quantidade_reservada),
                balance.custo_medio,
            )
            balance.quantidade_atual = 100
            balance.custo_medio = 5
            person_id, identity = await _identity(session, context[0], context[1])
            operation_id = await _create_operation(session, context, "consumos-parciais")
            operation_ids.append(operation_id)
            request_id, item_id = await _create_request(
                session, context, person_id, 100, "CONSUMIVEL", operation_id
            )
            request_ids.append(request_id)
            unit_id = (
                await session.execute(
                    select(UnidadeMedida.id).where(UnidadeMedida.ativo.is_(True)).limit(1)
                )
            ).scalar_one()
            execution = OperacaoExecucao(
                tenant_id=context[0],
                operacao_id=operation_id,
                production_unit_id=context[10],
                data_execucao=date.today(),
                quantidade_executada=1,
                quantidade_devolvida=0,
                unidade_medida_id=unit_id,
                status="REALIZADA",
            )
            session.add(execution)
            await session.flush()
            execution_id = execution.id
            await session.commit()

        delivery_id, _ = await _deliver(factory, context, request_id, item_id, context[1], 100)
        device_id, _ = await _receive(
            factory, context, request_id, item_id, delivery_id, context[1], 100
        )

        event_ids = []
        async with factory() as session:
            await _tenant_context(session, context[0])
            request = await session.get(RequisicaoMaterial, request_id)
            first = await RequisicaoPosseService(session, context[0]).destinar(
                request_id,
                DestinacaoRequisicaoRequest(
                    item_id=item_id,
                    entrega_evento_id=delivery_id,
                    tipo_evento="CONSUMO",
                    quantidade=30,
                    base_version=request.version,
                    client_operation_id=f"01G-PARTIAL-1-{request_id}",
                    dispositivo_id=device_id,
                    operacao_execucao_id=execution_id,
                ),
                usuario_id=context[1],
                dispositivo_id=device_id,
            )
            await session.commit()
            event_ids.append(first.evento_id)

        async with factory() as session:
            await _tenant_context(session, context[0])
            request = await session.get(RequisicaoMaterial, request_id)
            second = await RequisicaoPosseService(session, context[0]).destinar(
                request_id,
                DestinacaoRequisicaoRequest(
                    item_id=item_id,
                    entrega_evento_id=delivery_id,
                    tipo_evento="CONSUMO",
                    quantidade=20,
                    base_version=request.version,
                    client_operation_id=f"01G-PARTIAL-2-{request_id}",
                    dispositivo_id=device_id,
                    operacao_execucao_id=execution_id,
                ),
                usuario_id=context[1],
                dispositivo_id=device_id,
            )
            await session.commit()
            event_ids.append(second.evento_id)

        async with factory() as session:
            await _tenant_context(session, context[0])
            relay = DomainEventOutboxRelay(
                session,
                service=DomainEventOutboxService(session, context[0]),
            )
            relay_result = await relay.run_once(
                tenant_id=context[0],
                event_type="operational.material_request.consumo",
            )
            assert relay_result.processed == 2
            allocations = (
                await session.execute(
                    select(CostAllocation).where(
                        CostAllocation.tenant_id == context[0],
                        CostAllocation.requisicao_item_evento_id.in_(event_ids),
                    )
                )
            ).scalars().all()
            assert len(allocations) == 2
            assert sum(float(allocation.amount) for allocation in allocations) == 250
            assert all(
                allocation.operation_execution_id == execution_id for allocation in allocations
            )
            await session.rollback()
    finally:
        if context is not None:
            await _restore_cost_average(factory, context)
            await _cleanup(factory, context, request_ids, operation_ids, identity)
        await engine.dispose()
