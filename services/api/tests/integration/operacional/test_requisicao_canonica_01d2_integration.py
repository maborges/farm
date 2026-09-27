"""Provas transacionais reais do fluxo canônico 01D2.

Executar somente contra um PostgreSQL de desenvolvimento controlado:

    DEEPFARMS_RUN_REAL_01D2=1 pytest -q tests/integration/operacional/test_requisicao_canonica_01d2_integration.py
"""

from __future__ import annotations

import asyncio
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agricola.operacoes.models import OperacaoAgricola
from agricola.operacoes.service import OperacaoService
from core.cadastros.models import ProdutoCatalogo
from core.cadastros.produtos.models import ProdutoEstoque
from core.exceptions import BusinessRuleError, EntityNotFoundError, TenantViolationError
from core.models.auth import Usuario
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from operacional.models.estoque import (
    Deposito,
    EstoqueMovimento,
    ItemRequisicao,
    LoteEstoque,
    RequisicaoItemEvento,
    RequisicaoMaterial,
    ReservaEstoque,
    SaldoEstoque,
)
from operacional.schemas.estoque import (
    ItemEntregaUpdate,
    RequisicaoEntregarRequest,
    RequisicaoItemOperacaoCanonicaRequest,
    ReservaItemCanonicaRequest,
)
from operacional.services import EstoqueService
from operacional.services.requisicao_canonica_service import RequisicaoCanonicaService


pytestmark = pytest.mark.skipif(
    os.getenv("DEEPFARMS_RUN_REAL_01D2") != "1",
    reason="prova PostgreSQL real opt-in",
)


def _create_real_engine():
    return create_async_engine(
        os.environ["DATABASE_URL"],
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=False,
        connect_args={"timeout": 30, "ssl": False, "server_settings": {"search_path": "farms"}},
    )


async def _prewarm_real_engine(engine) -> None:
    first = await engine.connect()
    second = None
    try:
        second = await engine.connect()
        await first.execute(text("select 1"))
        await second.execute(text("select 1"))
    finally:
        if second is not None:
            await second.close()
        await first.close()


async def _tenant_context(session, tenant_id: UUID) -> None:
    await session.execute(
        text("select set_config('app.current_tenant_id', :tenant, true)"),
        {"tenant": str(tenant_id)},
    )


async def _new_request(session, *, tenant_id, unit_id, user_id, product_id, depot_id, quantity, name, operation_id=None):
    request = RequisicaoMaterial(
        tenant_id=tenant_id,
        numero=f"T01D2-{name[:12]}-{uuid4().hex[:8]}",
        unidade_produtiva_id=unit_id,
        solicitante_id=user_id,
        status="APROVADA",
        origem_tipo="ORDEM_SERVICO" if operation_id else "OUTRO",
        operacao_agricola_id=operation_id,
    )
    session.add(request)
    await session.flush()
    item = ItemRequisicao(
        tenant_id=tenant_id,
        requisicao_id=request.id,
        produto_id=product_id,
        deposito_id=depot_id,
        quantidade_solicitada=quantity,
        quantidade_aprovada=quantity,
        natureza_item="CONSUMIVEL",
    )
    session.add(item)
    await session.flush()
    return request.id, item.id


async def _reserve_and_pick(session, tenant_id, ids, quantity, depot_id, user_id, name):
    service = RequisicaoCanonicaService(session, tenant_id)
    await service.reservar_item(
        ids[0],
        ids[1],
        ReservaItemCanonicaRequest(
            quantidade=quantity,
            deposito_id=depot_id,
            client_operation_id=f"01D2-RESERVE-{name}",
        ),
        user_id,
    )
    await service.separar_item(
        ids[0],
        ids[1],
        RequisicaoItemOperacaoCanonicaRequest(
            quantidade=quantity,
            client_operation_id=f"01D2-PICK-{name}",
        ),
        user_id,
    )


async def _delete_request_rows(session, tenant_id: UUID, request_ids: list[UUID]) -> None:
    await _tenant_context(session, tenant_id)
    if not request_ids:
        return
    params = {"ids": [str(value) for value in request_ids]}
    await session.execute(
        text("alter table farms.estoque_requisicao_item_eventos disable trigger trg_estoque_requisicao_item_evento_append_only")
    )
    await session.execute(
        text("alter table farms.estoque_movimentos disable trigger tg_estoque_movimentos_append_only")
    )
    statements = (
        "delete from farms.estoque_movimentos where requisicao_item_evento_id in (select id from farms.estoque_requisicao_item_eventos where requisicao_id=any(cast(:ids as uuid[])))",
        "delete from farms.domain_event_outbox where source_id in (select id::text from farms.estoque_requisicao_item_eventos where requisicao_id=any(cast(:ids as uuid[])))",
        "delete from farms.estoque_requisicao_item_eventos where requisicao_id=any(cast(:ids as uuid[]))",
        "delete from farms.estoque_reservas where item_requisicao_id in (select id from farms.estoque_requisicoes_itens where requisicao_id=any(cast(:ids as uuid[])))",
        "delete from farms.estoque_requisicoes_itens where requisicao_id=any(cast(:ids as uuid[]))",
        "delete from farms.estoque_requisicoes where id=any(cast(:ids as uuid[]))",
    )
    for statement in statements:
        await session.execute(text(statement), params)
    await session.execute(
        text("alter table farms.estoque_requisicao_item_eventos enable trigger trg_estoque_requisicao_item_evento_append_only")
    )
    await session.execute(
        text("alter table farms.estoque_movimentos enable trigger tg_estoque_movimentos_append_only")
    )


async def _delete_test_rows(session, tenant_id: UUID) -> None:
    await _tenant_context(session, tenant_id)
    request_ids = [
        row[0]
        for row in (
            await session.execute(
                text("select id from farms.estoque_requisicoes where numero like 'T01D2-%'")
            )
        ).all()
    ]
    await _delete_request_rows(session, tenant_id, request_ids)


async def test_requisicao_canonica_01d2_all_transactional_proofs() -> None:
    engine = _create_real_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    created: dict[str, tuple[UUID, UUID]] = {}
    balance_id = tenant_id = None
    original_balance = None
    other_tenant = None
    cross_depot_id = None
    cross_balance_id = None
    cross_lot_id = None
    try:
        await _prewarm_real_engine(engine)
        async with session_factory() as session:
            context = (
                await session.execute(
                    select(
                        Tenant.id,
                        Usuario.id,
                        UnidadeProdutiva.id,
                        ProdutoCatalogo.id,
                        Deposito.id,
                        SaldoEstoque.id,
                    )
                    .select_from(Tenant)
                        .join(Usuario, Usuario.ativo.is_(True))
                        .join(UnidadeProdutiva, UnidadeProdutiva.tenant_id == Tenant.id)
                        .join(ProdutoCatalogo, (ProdutoCatalogo.tenant_id == Tenant.id) | ProdutoCatalogo.tenant_id.is_(None))
                        .outerjoin(ProdutoEstoque, ProdutoEstoque.produto_id == ProdutoCatalogo.id)
                        .join(Deposito, (Deposito.tenant_id == Tenant.id) & (Deposito.unidade_produtiva_id == UnidadeProdutiva.id))
                        .join(SaldoEstoque, (SaldoEstoque.deposito_id == Deposito.id) & (SaldoEstoque.produto_id == ProdutoCatalogo.id))
                        .where(
                            Tenant.ativo.is_(True),
                            SaldoEstoque.quantidade_reservada == 0,
                            (ProdutoEstoque.id.is_(None) | (ProdutoEstoque.requer_receituario.is_(False))),
                        )
                    .limit(1)
                )
            ).first()
            assert context is not None, "contexto de teste não encontrado"
            tenant_id, user_id, unit_id, product_id, depot_id, balance_id = context
            other_tenant = (
                await session.execute(select(Tenant.id).where(Tenant.id != tenant_id, Tenant.ativo.is_(True)).limit(1))
            ).scalar_one_or_none()
            assert other_tenant is not None, "Tenant B não encontrado para prova cross-tenant"
            other_unit_id = (await session.execute(
                select(UnidadeProdutiva.id).where(UnidadeProdutiva.tenant_id == other_tenant).limit(1)
            )).scalar_one_or_none()
            assert other_unit_id is not None, "Unidade produtiva B não encontrada para prova cross-tenant"
            await _tenant_context(session, other_tenant)
            cross_depot = Deposito(
                tenant_id=other_tenant,
                unidade_produtiva_id=other_unit_id,
                nome=f"T01D3-DEPOT-B-{uuid4().hex[:8]}",
                tipo="GERAL",
            )
            session.add(cross_depot)
            await session.flush()
            other_depot_id = cross_depot.id
            cross_depot_id = other_depot_id
            cross_balance = SaldoEstoque(
                deposito_id=other_depot_id,
                produto_id=product_id,
                quantidade_atual=1,
                quantidade_reservada=0,
            )
            session.add(cross_balance)
            await session.flush()
            cross_balance_id = cross_balance.id
            cross_lot = LoteEstoque(
                produto_id=product_id,
                deposito_id=other_depot_id,
                numero_lote=f"T01D3-B-{uuid4().hex[:8]}",
                quantidade_inicial=1,
                quantidade_atual=1,
                custo_unitario=1,
                status="ATIVO",
            )
            session.add(cross_lot)
            await session.flush()
            cross_lot_id = cross_lot.id
            await _tenant_context(session, tenant_id)
            operation_id = (
                await session.execute(select(OperacaoAgricola.id).where(OperacaoAgricola.tenant_id == tenant_id).limit(1))
            ).scalar_one_or_none()
            assert operation_id is not None, "operação real para prova FIFO não encontrada"
            await _tenant_context(session, tenant_id)
            balance = await session.get(SaldoEstoque, balance_id, with_for_update=True)
            original_balance = (float(balance.quantidade_atual), float(balance.quantidade_reservada))
            balance.quantidade_atual = 100
            created["same"] = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=30, name="same")
            created["version"] = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=10, name="version")
            created["atomic"] = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=5, name="atomic")
            created["legacy"] = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=20, name="legacy")
            created["fifo"] = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=5, name="fifo", operation_id=operation_id)
            created["fifo_reserved"] = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=1, name="fifo-reserved", operation_id=operation_id)
            created["cross"] = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=1, name="cross")
            await session.commit()

        # Two different requests compete at the real reservation boundary.
        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            comp_a = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=70, name="competition-a")
            comp_b = await _new_request(session, tenant_id=tenant_id, unit_id=unit_id, user_id=user_id, product_id=product_id, depot_id=depot_id, quantity=70, name="competition-b")
            await session.commit()

        async def reserve_competitor(ids, name):
            async with session_factory() as session:
                await _tenant_context(session, tenant_id)
                try:
                    await RequisicaoCanonicaService(session, tenant_id).reservar_item(
                        ids[0], ids[1], ReservaItemCanonicaRequest(quantidade=70, deposito_id=depot_id, client_operation_id=f"01D2-COMP-{name}"), user_id
                    )
                    await session.commit()
                    return "SUCCESS"
                except Exception as exc:
                    await session.rollback()
                    return type(exc).__name__

        competition = await asyncio.gather(reserve_competitor(comp_a, "A"), reserve_competitor(comp_b, "B"))
        assert sorted(competition) == ["BusinessRuleError", "SUCCESS"]
        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            balance = await session.get(SaldoEstoque, balance_id)
            assert float(balance.quantidade_atual) == 100
            winner_reservations = (await session.execute(
                select(func.count(), func.coalesce(func.sum(ReservaEstoque.quantidade), 0))
                .where(ReservaEstoque.item_requisicao_id.in_([comp_a[1], comp_b[1]]), ReservaEstoque.status == "ATIVA")
            )).one()
            assert winner_reservations[0] == 1
            assert float(winner_reservations[1]) == 70
            assert float(balance.quantidade_reservada) == 70
            await _delete_request_rows(session, tenant_id, [comp_a[0], comp_b[0]])
            balance.quantidade_atual = 100
            balance.quantidade_reservada = original_balance[1]
            await session.commit()

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            balance_before_cross = await session.get(SaldoEstoque, balance_id)
            cross_balance_before = await session.get(SaldoEstoque, cross_balance_id)
            lot_before_cross = (await session.execute(
                select(LoteEstoque.quantidade_atual).where(LoteEstoque.id == cross_lot_id)
            )).scalar_one()
            with pytest.raises((EntityNotFoundError, BusinessRuleError, TenantViolationError)):
                await RequisicaoCanonicaService(session, tenant_id).reservar_item(
                    created["cross"][0],
                    created["cross"][1],
                    ReservaItemCanonicaRequest(
                        quantidade=1,
                        deposito_id=other_depot_id,
                        client_operation_id="01D2-CROSS-DEPOT-RESERVE",
                    ),
                    user_id,
                )
            await session.rollback()
            await _tenant_context(session, tenant_id)
            balance_after_cross = await session.get(SaldoEstoque, balance_id)
            cross_balance_after = await session.get(SaldoEstoque, cross_balance_id)
            lot_after_cross = (await session.execute(
                select(LoteEstoque.quantidade_atual).where(LoteEstoque.id == cross_lot_id)
            )).scalar_one()
            assert float(balance_after_cross.quantidade_atual) == float(balance_before_cross.quantidade_atual)
            assert float(balance_after_cross.quantidade_reservada) == float(balance_before_cross.quantidade_reservada)
            assert float(lot_after_cross) == float(lot_before_cross)
            assert float(cross_balance_after.quantidade_atual) == float(cross_balance_before.quantidade_atual)
            assert float(cross_balance_after.quantidade_reservada) == float(cross_balance_before.quantidade_reservada)

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            await RequisicaoCanonicaService(session, tenant_id).reservar_item(
                created["fifo_reserved"][0],
                created["fifo_reserved"][1],
                ReservaItemCanonicaRequest(
                    quantidade=1,
                    deposito_id=depot_id,
                    client_operation_id="01D2-FIFO-RESERVE-ONLY",
                ),
                user_id,
            )
            await session.commit()

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            reserved_request, _ = await OperacaoService(
                session, tenant_id
            )._requisicao_entregue_da_operacao(operation_id)
            assert reserved_request is not None
            assert reserved_request.id == created["fifo_reserved"][0]
            assert reserved_request.status == "APROVADA"

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            await RequisicaoCanonicaService(session, tenant_id).reservar_item(
                created["cross"][0],
                created["cross"][1],
                ReservaItemCanonicaRequest(
                    quantidade=1,
                    deposito_id=depot_id,
                    client_operation_id="01D2-CROSS-VALID-RESERVE",
                ),
                user_id,
            )
            await session.commit()

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            balance_before_cross_item = await session.get(SaldoEstoque, balance_id)
            cross_balance_before_item = await session.get(SaldoEstoque, cross_balance_id)
            lot_before_cross_item = (await session.execute(
                select(LoteEstoque.quantidade_atual).where(LoteEstoque.id == cross_lot_id)
            )).scalar_one()
            with pytest.raises((EntityNotFoundError, BusinessRuleError, TenantViolationError)):
                await RequisicaoCanonicaService(session, tenant_id).separar_item(
                    created["cross"][0],
                    created["cross"][1],
                    RequisicaoItemOperacaoCanonicaRequest(
                        quantidade=1,
                        lote_id=cross_lot_id,
                        client_operation_id="01D2-CROSS-LOT-PICK",
                    ),
                    user_id,
                )
            await session.rollback()
            await _tenant_context(session, tenant_id)
            with pytest.raises((EntityNotFoundError, BusinessRuleError, TenantViolationError)):
                await RequisicaoCanonicaService(session, tenant_id).entregar_item(
                    created["cross"][0],
                    created["cross"][1],
                    RequisicaoItemOperacaoCanonicaRequest(
                        quantidade=1,
                        lote_id=cross_lot_id,
                        client_operation_id="01D2-CROSS-LOT-DELIVERY",
                    ),
                    user_id,
                )
            await session.rollback()
            await _tenant_context(session, tenant_id)
            balance_after_cross_item = await session.get(SaldoEstoque, balance_id)
            cross_balance_after_item = await session.get(SaldoEstoque, cross_balance_id)
            lot_after_cross_item = (await session.execute(
                select(LoteEstoque.quantidade_atual).where(LoteEstoque.id == cross_lot_id)
            )).scalar_one()
            assert float(balance_after_cross_item.quantidade_atual) == float(balance_before_cross_item.quantidade_atual)
            assert float(balance_after_cross_item.quantidade_reservada) == float(balance_before_cross_item.quantidade_reservada)
            assert float(lot_after_cross_item) == float(lot_before_cross_item)
            assert float(cross_balance_after_item.quantidade_atual) == float(cross_balance_before_item.quantidade_atual)
            assert float(cross_balance_after_item.quantidade_reservada) == float(cross_balance_before_item.quantidade_reservada)

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            with pytest.raises(BusinessRuleError):
                await EstoqueService(session, tenant_id).entregar_requisicao(
                    created["cross"][0],
                    RequisicaoEntregarRequest(
                        itens=[
                            ItemEntregaUpdate(
                                item_id=created["cross"][1],
                                quantidade_entregue=1,
                            )
                        ]
                    ),
                )
            await session.rollback()

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            for name, quantity in (("same", 30), ("version", 10), ("atomic", 5), ("legacy", 20), ("fifo", 5)):
                await _reserve_and_pick(session, tenant_id, created[name], quantity, depot_id, user_id, name)
            await session.commit()

        async def same_key_client():
            async with session_factory() as session:
                await _tenant_context(session, tenant_id)
                try:
                    event, movement = await RequisicaoCanonicaService(session, tenant_id).entregar_item(
                        created["same"][0], created["same"][1], RequisicaoItemOperacaoCanonicaRequest(quantidade=30, client_operation_id="01D2-SAME"), user_id
                    )
                    await session.commit()
                    return str(event.id), str(movement.id)
                except Exception:
                    await session.rollback()
                    raise

        same_results = await asyncio.gather(same_key_client(), same_key_client())
        assert same_results[0] == same_results[1]
        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            assert (await session.execute(
                select(func.count()).select_from(RequisicaoItemEvento).where(RequisicaoItemEvento.client_operation_id == "01D2-SAME")
            )).scalar_one() == 1
            assert (await session.execute(
                select(func.count()).select_from(EstoqueMovimento).where(EstoqueMovimento.requisicao_item_evento_id == UUID(same_results[0][0]))
            )).scalar_one() == 1

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            request = await session.get(RequisicaoMaterial, created["version"][0], with_for_update=True)
            version = request.version
            await RequisicaoCanonicaService(session, tenant_id).entregar_item(
                created["version"][0], created["version"][1], RequisicaoItemOperacaoCanonicaRequest(quantidade=10, base_version=version, client_operation_id="01D2-VERSION-ORIGINAL"), user_id
            )
            await session.commit()
        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            with pytest.raises(BusinessRuleError):
                await RequisicaoCanonicaService(session, tenant_id).entregar_item(
                    created["version"][0], created["version"][1], RequisicaoItemOperacaoCanonicaRequest(quantidade=10, base_version=version, client_operation_id="01D2-VERSION-OTHER"), user_id
                )
            await session.rollback()
        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            retry_event, _ = await RequisicaoCanonicaService(session, tenant_id).entregar_item(
                created["version"][0], created["version"][1], RequisicaoItemOperacaoCanonicaRequest(quantidade=10, base_version=version, client_operation_id="01D2-VERSION-ORIGINAL"), user_id
            )
            assert str(retry_event.id) == str((await session.execute(select(RequisicaoItemEvento.id).where(RequisicaoItemEvento.client_operation_id == "01D2-VERSION-ORIGINAL"))).scalar_one())
            await session.rollback()

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            before = (await session.execute(select(SaldoEstoque.quantidade_atual).where(SaldoEstoque.id == balance_id))).scalar_one()
            atomic_request = await session.get(RequisicaoMaterial, created["atomic"][0])
            atomic_reservation = (await session.execute(select(ReservaEstoque).where(ReservaEstoque.item_requisicao_id == created["atomic"][1]))).scalar_one()
            before_atomic_version = atomic_request.version
            before_atomic_reserved_consumed = float(atomic_reservation.quantidade_consumida)
            before_atomic_outbox = (await session.execute(text("select count(*) from farms.domain_event_outbox where tenant_id=:tenant"), {"tenant": str(tenant_id)})).scalar_one()
            service = RequisicaoCanonicaService(session, tenant_id)

            async def fail_enqueue(*_args, **_kwargs):
                raise RuntimeError("01D2 controlled rollback")

            service._enqueue = fail_enqueue
            with pytest.raises(RuntimeError):
                await service.entregar_item(
                    created["atomic"][0], created["atomic"][1], RequisicaoItemOperacaoCanonicaRequest(quantidade=5, base_version=3, client_operation_id="01D2-ATOMIC"), user_id
                )
            await session.rollback()
        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            after = (await session.execute(select(SaldoEstoque.quantidade_atual).where(SaldoEstoque.id == balance_id))).scalar_one()
            assert float(after) == float(before)
            atomic_request = await session.get(RequisicaoMaterial, created["atomic"][0])
            atomic_reservation = (await session.execute(select(ReservaEstoque).where(ReservaEstoque.item_requisicao_id == created["atomic"][1]))).scalar_one()
            assert atomic_request.version == before_atomic_version
            assert float(atomic_reservation.quantidade_consumida) == before_atomic_reserved_consumed
            assert (await session.execute(text("select count(*) from farms.domain_event_outbox where tenant_id=:tenant"), {"tenant": str(tenant_id)})).scalar_one() == before_atomic_outbox
            assert (await session.execute(select(func.count()).select_from(RequisicaoItemEvento).where(RequisicaoItemEvento.client_operation_id == "01D2-ATOMIC"))).scalar_one() == 0
            assert (await session.execute(select(func.count()).select_from(EstoqueMovimento).where(EstoqueMovimento.origem_id == created["atomic"][0]))).scalar_one() == 0

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            legacy_movements_before = (await session.execute(
                select(func.count()).select_from(EstoqueMovimento).where(EstoqueMovimento.origem_id == created["legacy"][0])
            )).scalar_one()
            with pytest.raises(BusinessRuleError):
                await EstoqueService(session, tenant_id).entregar_requisicao(
                    created["legacy"][0], RequisicaoEntregarRequest(itens=[ItemEntregaUpdate(item_id=created["legacy"][1], quantidade_entregue=20)])
                )
            await session.rollback()
            await _tenant_context(session, tenant_id)
            legacy_movements_after = (await session.execute(
                select(func.count()).select_from(EstoqueMovimento).where(EstoqueMovimento.origem_id == created["legacy"][0])
            )).scalar_one()
            assert legacy_movements_after == legacy_movements_before == 0

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            await RequisicaoCanonicaService(session, tenant_id).entregar_item(
                created["legacy"][0], created["legacy"][1], RequisicaoItemOperacaoCanonicaRequest(quantidade=20, base_version=3, client_operation_id="01D2-LEGACY-CANONICAL"), user_id
            )
            await session.commit()

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            fifo_operation_id = operation_id
            await RequisicaoCanonicaService(session, tenant_id).entregar_item(
                created["fifo"][0], created["fifo"][1], RequisicaoItemOperacaoCanonicaRequest(quantidade=3, base_version=3, client_operation_id="01D2-FIFO-PARTIAL"), user_id
            )
            await session.commit()
        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            partial_reservation = (await session.execute(select(ReservaEstoque).where(ReservaEstoque.item_requisicao_id == created["fifo"][1]))).scalar_one()
            assert partial_reservation.status == "PARCIALMENTE_CONSUMIDA"
            assert float(partial_reservation.quantidade) == 5
            assert float(partial_reservation.quantidade_consumida) == 3
        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            fifo_operation = await session.get(OperacaoAgricola, fifo_operation_id)
            before_fifo_movements = (await session.execute(select(func.count()).select_from(EstoqueMovimento).where(EstoqueMovimento.origem_id == created["fifo"][0]))).scalar_one()
            before_fifo_balance = (await session.execute(select(SaldoEstoque.quantidade_atual).where(SaldoEstoque.id == balance_id))).scalar_one()
            with pytest.raises(BusinessRuleError):
                await OperacaoService(session, tenant_id)._aplicar_insumos_na_operacao(fifo_operation, [], unidade_produtiva_id=unit_id, area_base_ha=1)
            await session.rollback()
            await _tenant_context(session, tenant_id)
            after_fifo_movements = (await session.execute(select(func.count()).select_from(EstoqueMovimento).where(EstoqueMovimento.origem_id == created["fifo"][0]))).scalar_one()
            after_fifo_balance = (await session.execute(select(SaldoEstoque.quantidade_atual).where(SaldoEstoque.id == balance_id))).scalar_one()
            assert after_fifo_movements == before_fifo_movements
            assert float(after_fifo_balance) == float(before_fifo_balance)

        async with session_factory() as session:
            await _tenant_context(session, tenant_id)
            event = (await session.execute(select(RequisicaoItemEvento).where(RequisicaoItemEvento.client_operation_id == "01D2-SAME"))).scalar_one()
            movement = (await session.execute(select(EstoqueMovimento).where(EstoqueMovimento.requisicao_item_evento_id == event.id))).scalar_one()
            event_id = event.id
            movement_values = {
                "produto_id": movement.produto_id,
                "deposito_id": movement.deposito_id,
                "lote_id": movement.lote_id,
                "quantidade": movement.quantidade,
                "unidade_medida_id": movement.unidade_medida_id,
                "origem_id": movement.origem_id,
            }
            with pytest.raises(DBAPIError):
                await session.execute(text("update farms.estoque_requisicao_item_eventos set motivo='x' where id=:id"), {"id": str(event_id)})
            await session.rollback()
            await _tenant_context(session, tenant_id)
            with pytest.raises(DBAPIError):
                await session.execute(text("delete from farms.estoque_requisicao_item_eventos where id=:id"), {"id": str(event_id)})
            await session.rollback()
            duplicate = EstoqueMovimento(
                tenant_id=tenant_id,
                produto_id=movement_values["produto_id"],
                deposito_id=movement_values["deposito_id"],
                lote_id=movement_values["lote_id"],
                quantidade=movement_values["quantidade"],
                unidade_medida_id=movement_values["unidade_medida_id"],
                tipo_movimento="SAIDA",
                origem="REQUISICAO",
                origem_id=movement_values["origem_id"],
                requisicao_item_evento_id=event_id,
            )
            session.add(duplicate)
            with pytest.raises(IntegrityError):
                await session.flush()
            await session.rollback()
            assert (await session.execute(select(func.count()).select_from(EstoqueMovimento).where(EstoqueMovimento.requisicao_item_evento_id == event_id))).scalar_one() == 1

        if other_tenant is not None:
            async with session_factory() as session:
                await _tenant_context(session, other_tenant)
                with pytest.raises((EntityNotFoundError, BusinessRuleError)):
                    await RequisicaoCanonicaService(session, other_tenant).reservar_item(
                        created["cross"][0], created["cross"][1], ReservaItemCanonicaRequest(quantidade=1, deposito_id=depot_id, client_operation_id="01D2-CROSS"), user_id
                    )
                await session.rollback()
    finally:
        if tenant_id is not None:
            async with session_factory() as session:
                await _tenant_context(session, tenant_id)
                await _delete_test_rows(session, tenant_id)
                if cross_lot_id is not None:
                    await _tenant_context(session, other_tenant)
                    await session.execute(
                        text("delete from farms.estoque_lotes where id=:id"),
                        {"id": str(cross_lot_id)},
                    )
                if cross_balance_id is not None:
                    await session.execute(
                        text("delete from farms.estoque_saldos where id=:id"),
                        {"id": str(cross_balance_id)},
                    )
                if cross_depot_id is not None:
                    await session.execute(
                        text("delete from farms.estoque_depositos where id=:id"),
                        {"id": str(cross_depot_id)},
                    )
                    await _tenant_context(session, tenant_id)
                balance = await session.get(SaldoEstoque, balance_id, with_for_update=True)
                if original_balance is not None:
                    balance.quantidade_atual, balance.quantidade_reservada = original_balance
                await session.commit()
        await engine.dispose()
