"""Certificação PostgreSQL real das lacunas finais do fluxo 01F1."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import String, delete, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola
from agricola.operacoes.schemas import OperacaoAgricolaUpdate
from agricola.operacoes.service import OperacaoService
from core.cadastros.models import ProdutoCatalogo
from core.cadastros.pessoas.models import Pessoa, PessoaUsuario
from core.cadastros.produtos.models import ProdutoEstoque
from core.exceptions import BusinessRuleError
from core.models.auth import TenantUsuario, Usuario
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from events.outbox_model import DomainEventOutbox
from operacional.models.estoque import (
    Deposito,
    EstoqueMovimento,
    ItemRequisicao,
    RequisicaoItemEvento,
    RequisicaoMaterial,
    ReservaEstoque,
    SaldoEstoque,
)
from operacional.schemas.estoque import (
    DestinacaoRequisicaoRequest,
    RecebimentoRequisicaoRequest,
    RequisicaoItemOperacaoCanonicaRequest,
    ReservaItemCanonicaRequest,
)
from operacional.services.requisicao_canonica_service import RequisicaoCanonicaService
from operacional.services.requisicao_posse_service import RequisicaoPosseService
from operacional.services.requisicao_recebimento_service import RequisicaoRecebimentoService

pytestmark = pytest.mark.skipif(
    os.getenv("DEEPFARMS_RUN_REAL_01F1") != "1",
    reason="certificação PostgreSQL real 01F1 opt-in",
)


def _engine():
    return create_async_engine(
        os.environ["DATABASE_URL"],
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=False,
        connect_args={"timeout": 30, "ssl": False, "server_settings": {"search_path": "farms"}},
    )


async def _prewarm_real_engine(engine) -> None:
    """Abre as duas conexões do runner antes da primeira transação real.

    O PostgreSQL de integração usado pelo 01D3 apresentou falhas intermitentes
    ao abrir conexões sob concorrência do pool. O prewarm mantém a configuração
    certificada e torna a falha de conectividade explícita antes dos cenários.
    """
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


async def _context(session):
    row = (
        await session.execute(
            select(
                Tenant.id,
                TenantUsuario.usuario_id,
                UnidadeProdutiva.id,
                ProdutoCatalogo.id,
                Deposito.id,
                SaldoEstoque.id,
                OperacaoAgricola.id,
                OperacaoAgricola.safra_id,
                OperacaoAgricola.talhao_id,
                OperacaoAgricola.cultivo_id,
                OperacaoAgricola.production_unit_id,
                OperacaoAgricola.tipo,
            )
            .select_from(Tenant)
            .join(TenantUsuario, TenantUsuario.tenant_id == Tenant.id)
            .join(Usuario, Usuario.id == TenantUsuario.usuario_id)
            .join(UnidadeProdutiva, UnidadeProdutiva.tenant_id == Tenant.id)
            .join(
                ProdutoCatalogo,
                (ProdutoCatalogo.tenant_id == Tenant.id) | ProdutoCatalogo.tenant_id.is_(None),
            )
            .outerjoin(ProdutoEstoque, ProdutoEstoque.produto_id == ProdutoCatalogo.id)
            .join(
                Deposito,
                (Deposito.tenant_id == Tenant.id)
                & (Deposito.unidade_produtiva_id == UnidadeProdutiva.id),
            )
            .join(
                SaldoEstoque,
                (SaldoEstoque.deposito_id == Deposito.id)
                & (SaldoEstoque.produto_id == ProdutoCatalogo.id),
            )
            .join(OperacaoAgricola, OperacaoAgricola.tenant_id == Tenant.id)
            .where(
                Tenant.ativo.is_(True),
                TenantUsuario.status == "ATIVO",
                Usuario.ativo.is_(True),
                SaldoEstoque.quantidade_reservada == 0,
                (ProdutoEstoque.id.is_(None) | (ProdutoEstoque.requer_receituario.is_(False))),
            )
            .limit(1)
        )
    ).first()
    assert row is not None, "contexto 01F1 não encontrado"
    return row


async def _identity(session, tenant_id: UUID, user_id: UUID):
    identity = (
        (
            await session.execute(
                select(PessoaUsuario).where(
                    PessoaUsuario.tenant_id == tenant_id,
                    PessoaUsuario.usuario_id == user_id,
                    PessoaUsuario.status == "ATIVO",
                )
            )
        )
        .scalars()
        .first()
    )
    if identity is not None:
        return identity.pessoa_id, None
    person = Pessoa(
        tenant_id=tenant_id,
        tipo="PF",
        nome_exibicao=f"T01F1 pessoa {uuid4().hex[:8]}",
    )
    session.add(person)
    await session.flush()
    identity = PessoaUsuario(
        tenant_id=tenant_id,
        pessoa_id=person.id,
        usuario_id=user_id,
        status="ATIVO",
        vigencia_inicio=datetime.now(timezone.utc) - timedelta(minutes=1),  # noqa: UP017
        motivo="fixture temporário 01F1",
    )
    session.add(identity)
    await session.flush()
    return person.id, (identity.id, person.id)


async def _create_operation(session, ctx, suffix: str) -> UUID:
    operation = OperacaoAgricola(
        tenant_id=ctx[0],
        safra_id=ctx[7],
        talhao_id=ctx[8],
        cultivo_id=ctx[9],
        production_unit_id=ctx[10],
        tipo=ctx[11] or "OUTROS",
        descricao=f"T01F1 {suffix}",
        data_realizada=date.today(),
        area_aplicada_ha=1,
        custo_total=0,
        custo_por_ha=0,
        status="PLANEJADA",
    )
    session.add(operation)
    await session.flush()
    return operation.id


async def _create_request(
    session, ctx, person_id: UUID, quantity: float, nature: str, operation_id: UUID
):
    request = RequisicaoMaterial(
        tenant_id=ctx[0],
        numero=f"T01F1-{uuid4().hex[:12]}",
        unidade_produtiva_id=ctx[2],
        solicitante_id=ctx[1],
        responsavel_pessoa_id=person_id,
        operacao_agricola_id=operation_id,
        status="APROVADA",
        origem_tipo="ORDEM_SERVICO",
    )
    session.add(request)
    await session.flush()
    item = ItemRequisicao(
        tenant_id=ctx[0],
        requisicao_id=request.id,
        produto_id=ctx[3],
        deposito_id=ctx[4],
        quantidade_solicitada=quantity,
        quantidade_aprovada=quantity,
        natureza_item=nature,
    )
    session.add(item)
    await session.flush()
    return request.id, item.id


async def _deliver(factory, ctx, request_id, item_id, user_id, quantity):
    async with factory() as session:
        await _tenant_context(session, ctx[0])
        service = RequisicaoCanonicaService(session, ctx[0])
        await service.reservar_item(
            request_id,
            item_id,
            ReservaItemCanonicaRequest(
                quantidade=quantity,
                deposito_id=ctx[4],
                client_operation_id=f"01F1-R-{request_id}",
            ),
            user_id,
        )
        await service.separar_item(
            request_id,
            item_id,
            RequisicaoItemOperacaoCanonicaRequest(
                quantidade=quantity,
                deposito_id=ctx[4],
                client_operation_id=f"01F1-P-{request_id}",
            ),
            user_id,
        )
        event, movement = await service.entregar_item(
            request_id,
            item_id,
            RequisicaoItemOperacaoCanonicaRequest(
                quantidade=quantity,
                deposito_id=ctx[4],
                client_operation_id=f"01F1-D-{request_id}",
            ),
            user_id,
        )
        await session.commit()
        return event.id, movement.id


async def _receive(
    factory,
    ctx,
    request_id,
    item_id,
    delivery_id,
    user_id,
    quantity,
    result="RECEBIDO_INTEGRAL",
    reason=None,
):
    device_id = uuid4()
    async with factory() as session:
        await _tenant_context(session, ctx[0])
        request = await session.get(RequisicaoMaterial, request_id)
        result_ack = await RequisicaoRecebimentoService(session, ctx[0]).receber(
            request_id,
            RecebimentoRequisicaoRequest(
                item_id=item_id,
                entrega_evento_id=delivery_id,
                quantidade_recebida=quantity,
                resultado=result,
                base_version=request.version,
                client_operation_id=f"01F1-C-{request_id}",
                dispositivo_id=device_id,
                motivo=reason,
            ),
            usuario_id=user_id,
            dispositivo_id=device_id,
        )
        await session.commit()
        return device_id, result_ack


async def _cleanup(factory, ctx, request_ids, operation_ids, identity):
    async with factory() as session:
        await _tenant_context(session, ctx[0])
        request_ids = list(request_ids)
        event_ids = select(RequisicaoItemEvento.id).where(
            RequisicaoItemEvento.requisicao_id.in_(request_ids)
        )
        item_ids = select(ItemRequisicao.id).where(
            ItemRequisicao.requisicao_id.in_(request_ids)
        )
        await session.execute(
            text(
                "alter table farms.estoque_requisicao_item_eventos "
                "disable trigger trg_estoque_requisicao_item_evento_append_only"
            )
        )
        await session.execute(
            text(
                "alter table farms.estoque_movimentos "
                "disable trigger tg_estoque_movimentos_append_only"
            )
        )
        await session.execute(
            delete(EstoqueMovimento).where(
                EstoqueMovimento.requisicao_item_evento_id.in_(event_ids)
            )
        )
        await session.execute(
            delete(CostAllocation).where(
                CostAllocation.requisicao_item_evento_id.in_(event_ids)
            )
        )
        await session.execute(
            delete(DomainEventOutbox).where(
                DomainEventOutbox.source_id.in_(
                    select(RequisicaoItemEvento.id.cast(String)).where(
                        RequisicaoItemEvento.requisicao_id.in_(request_ids)
                    )
                )
            )
        )
        await session.execute(
            delete(RequisicaoItemEvento).where(
                RequisicaoItemEvento.requisicao_id.in_(request_ids)
            )
        )
        await session.execute(
            delete(ReservaEstoque).where(ReservaEstoque.item_requisicao_id.in_(item_ids))
        )
        await session.execute(
            delete(ItemRequisicao).where(ItemRequisicao.requisicao_id.in_(request_ids))
        )
        await session.execute(
            delete(RequisicaoMaterial).where(RequisicaoMaterial.id.in_(request_ids))
        )
        await session.execute(
            text(
                "alter table farms.estoque_requisicao_item_eventos "
                "enable trigger trg_estoque_requisicao_item_evento_append_only"
            )
        )
        await session.execute(
            text(
                "alter table farms.estoque_movimentos "
                "enable trigger tg_estoque_movimentos_append_only"
            )
        )
        if operation_ids:
            await session.execute(
                delete(OperacaoAgricola).where(OperacaoAgricola.id.in_(operation_ids))
            )
        balance = await session.get(SaldoEstoque, ctx[5], with_for_update=True)
        if balance is not None:
            balance.quantidade_atual = ctx[12]
            balance.quantidade_reservada = ctx[13]
        if identity is not None:
            await session.execute(
                text("delete from farms.cadastros_pessoas_usuarios where id = :id"),
                {"id": str(identity[0])},
            )
            await session.execute(
                text("delete from farms.cadastros_pessoas where id = :id"), {"id": str(identity[1])}
            )
        await session.commit()


async def _snapshot(session, tenant_id: UUID, request_id: UUID, balance_id: UUID):
    await _tenant_context(session, tenant_id)
    balance = await session.get(SaldoEstoque, balance_id)
    events = (
        await session.execute(
            select(RequisicaoItemEvento.tipo_evento, func.count())
            .where(
                RequisicaoItemEvento.tenant_id == tenant_id,
                RequisicaoItemEvento.requisicao_id == request_id,
            )
            .group_by(RequisicaoItemEvento.tipo_evento)
        )
    ).all()
    movements = (
        await session.execute(
            select(func.count())
            .select_from(EstoqueMovimento)
            .where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem_id == request_id,
                EstoqueMovimento.origem == "REQUISICAO",
            )
        )
    ).scalar_one()
    return (
        float(balance.quantidade_atual),
        balance.quantidade_reservada,
        dict(events),
        movements,
    )


@pytest.mark.asyncio
async def test_retornavel_3_devolve_2_danifica_1_sem_consumo_real():
    engine = _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    request_ids, operation_ids = [], []
    identity = None
    ctx = None
    try:
        await _prewarm_real_engine(engine)
        async with factory() as session:
            ctx = await _context(session)
            await _tenant_context(session, ctx[0])
            balance = await session.get(SaldoEstoque, ctx[5], with_for_update=True)
            ctx = (*ctx, float(balance.quantidade_atual), float(balance.quantidade_reservada))
            balance.quantidade_atual = 3
            person_id, identity = await _identity(session, ctx[0], ctx[1])
            request_id, item_id = await _create_request(
                session, ctx, person_id, 3, "RETORNAVEL", ctx[6]
            )
            request_ids.append(request_id)
            await session.commit()
        delivery_id, delivery_movement_id = await _deliver(
            factory, ctx, request_id, item_id, ctx[1], 3
        )
        device_id, received = await _receive(
            factory, ctx, request_id, item_id, delivery_id, ctx[1], 3
        )
        assert received.projection.itens[0].quantidade_em_posse == 3

        async with factory() as session:
            await _tenant_context(session, ctx[0])
            request = await session.get(RequisicaoMaterial, request_id)
            with pytest.raises(BusinessRuleError, match="retornável"):
                await RequisicaoPosseService(session, ctx[0]).destinar(
                    request_id,
                    DestinacaoRequisicaoRequest(
                        item_id=item_id,
                        entrega_evento_id=delivery_id,
                        tipo_evento="CONSUMO",
                        quantidade=1,
                        base_version=request.version,
                        client_operation_id=f"01F1-INVALID-CONSUME-{request_id}",
                        dispositivo_id=device_id,
                        operacao_execucao_id=uuid4(),
                    ),
                    usuario_id=ctx[1],
                    dispositivo_id=device_id,
                )
            await session.rollback()
            before = await _snapshot(session, ctx[0], request_id, ctx[5])
            assert before[2].get("CONSUMO", 0) == 0
            assert before[3] == 1

        async with factory() as session:
            await _tenant_context(session, ctx[0])
            request = await session.get(RequisicaoMaterial, request_id)
            damaged = await RequisicaoPosseService(session, ctx[0]).destinar(
                request_id,
                DestinacaoRequisicaoRequest(
                    item_id=item_id,
                    entrega_evento_id=delivery_id,
                    tipo_evento="DANO",
                    quantidade=1,
                    base_version=request.version,
                    client_operation_id=f"01F1-DAMAGE-{request_id}",
                    dispositivo_id=device_id,
                    motivo="ferramenta danificada",
                ),
                usuario_id=ctx[1],
                dispositivo_id=device_id,
            )
            await session.commit()
            assert damaged.projection.itens[0].quantidade_danificada == 1

        return_key = f"01F1-RETURN-{request_id}"
        async with factory() as session:
            await _tenant_context(session, ctx[0])
            request = await session.get(RequisicaoMaterial, request_id)
            returned = await RequisicaoPosseService(session, ctx[0]).destinar(
                request_id,
                DestinacaoRequisicaoRequest(
                    item_id=item_id,
                    entrega_evento_id=delivery_id,
                    tipo_evento="DEVOLUCAO",
                    quantidade=2,
                    base_version=request.version,
                    client_operation_id=return_key,
                    deposito_id=ctx[4],
                    dispositivo_id=device_id,
                ),
                usuario_id=ctx[1],
                dispositivo_id=device_id,
            )
            await session.commit()
            assert returned.projection.itens[0].quantidade_em_posse == 0
            assert returned.projection.itens[0].status_conciliacao == "CONCILIADO"
            assert returned.movimento_id is not None

        async with factory() as session:
            await _tenant_context(session, ctx[0])
            request = await session.get(RequisicaoMaterial, request_id)
            retry = await RequisicaoPosseService(session, ctx[0]).destinar(
                request_id,
                DestinacaoRequisicaoRequest(
                    item_id=item_id,
                    entrega_evento_id=delivery_id,
                    tipo_evento="DEVOLUCAO",
                    quantidade=2,
                    base_version=1,
                    client_operation_id=return_key,
                    deposito_id=ctx[4],
                    dispositivo_id=device_id,
                ),
                usuario_id=ctx[1],
                dispositivo_id=device_id,
            )
            await session.commit()
            assert retry.evento_id == returned.evento_id
            assert retry.movimento_id == returned.movimento_id
            metrics = await _snapshot(session, ctx[0], request_id, ctx[5])
            assert metrics[0] == 2
            assert metrics[2] == {
                "DANO": 1,
                "DEVOLUCAO": 1,
                "ENTREGA": 1,
                "RECEBIMENTO": 1,
                "SEPARACAO": 1,
            }
            assert metrics[3] == 2
            assert (
                await session.scalar(
                    select(func.sum(EstoqueMovimento.quantidade)).where(
                        EstoqueMovimento.tenant_id == ctx[0],
                        EstoqueMovimento.origem_id == request_id,
                        EstoqueMovimento.origem == "REQUISICAO",
                    )
                )
                == -1
            )
            assert await session.get(EstoqueMovimento, delivery_movement_id) is not None
    finally:
        if ctx is not None:
            await _cleanup(factory, ctx, request_ids, operation_ids, identity)
        await engine.dispose()


@pytest.mark.asyncio
async def test_devolucao_rollback_injetado_reexecuta_sem_efeito_parcial(monkeypatch):
    engine = _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    request_ids, operation_ids = [], []
    identity = None
    ctx = None
    try:
        await _prewarm_real_engine(engine)
        async with factory() as session:
            ctx = await _context(session)
            await _tenant_context(session, ctx[0])
            balance = await session.get(SaldoEstoque, ctx[5], with_for_update=True)
            ctx = (*ctx, float(balance.quantidade_atual), float(balance.quantidade_reservada))
            balance.quantidade_atual = 4
            person_id, identity = await _identity(session, ctx[0], ctx[1])
            request_id, item_id = await _create_request(
                session, ctx, person_id, 4, "CONSUMIVEL", ctx[6]
            )
            request_ids.append(request_id)
            await session.commit()
        delivery_id, _ = await _deliver(factory, ctx, request_id, item_id, ctx[1], 4)
        device_id, _ = await _receive(factory, ctx, request_id, item_id, delivery_id, ctx[1], 4)
        async with factory() as session:
            await _tenant_context(session, ctx[0])
            request = await session.get(RequisicaoMaterial, request_id)
            before = await _snapshot(session, ctx[0], request_id, ctx[5])
            before_version = request.version

            async def fail_enqueue(*args, **kwargs):
                raise RuntimeError("falha injetada 01F1 antes do commit")

            monkeypatch.setattr(RequisicaoPosseService, "_enqueue", fail_enqueue)
            with pytest.raises(RuntimeError, match="falha injetada"):
                await RequisicaoPosseService(session, ctx[0]).destinar(
                    request_id,
                    DestinacaoRequisicaoRequest(
                        item_id=item_id,
                        entrega_evento_id=delivery_id,
                        tipo_evento="DEVOLUCAO",
                        quantidade=4,
                        base_version=before_version,
                        client_operation_id=f"01F1-ROLLBACK-{request_id}",
                        deposito_id=ctx[4],
                        dispositivo_id=device_id,
                    ),
                    usuario_id=ctx[1],
                    dispositivo_id=device_id,
                )
            await session.rollback()

        async with factory() as session:
            await _tenant_context(session, ctx[0])
            request = await session.get(RequisicaoMaterial, request_id)
            after = await _snapshot(session, ctx[0], request_id, ctx[5])
            assert after == before
            assert request.version == before_version

        monkeypatch.undo()
        async with factory() as session:
            await _tenant_context(session, ctx[0])
            request = await session.get(RequisicaoMaterial, request_id)
            result = await RequisicaoPosseService(session, ctx[0]).destinar(
                request_id,
                DestinacaoRequisicaoRequest(
                    item_id=item_id,
                    entrega_evento_id=delivery_id,
                    tipo_evento="DEVOLUCAO",
                    quantidade=4,
                    base_version=request.version,
                    client_operation_id=f"01F1-ROLLBACK-{request_id}",
                    deposito_id=ctx[4],
                    dispositivo_id=device_id,
                ),
                usuario_id=ctx[1],
                dispositivo_id=device_id,
            )
            await session.commit()
            assert result.movimento_id is not None
            final = await _snapshot(session, ctx[0], request_id, ctx[5])
            assert final[2].get("DEVOLUCAO") == 1
            assert final[3] == 2
    finally:
        if ctx is not None:
            await _cleanup(factory, ctx, request_ids, operation_ids, identity)
        await engine.dispose()


@pytest.mark.asyncio
async def test_fechamento_bloqueia_posse_e_divergencia_e_libera_conciliada():
    engine = _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    request_ids, operation_ids = [], []
    identity = None
    ctx = None
    try:
        await _prewarm_real_engine(engine)
        async with factory() as session:
            ctx = await _context(session)
            await _tenant_context(session, ctx[0])
            balance = await session.get(SaldoEstoque, ctx[5], with_for_update=True)
            ctx = (*ctx, float(balance.quantidade_atual), float(balance.quantidade_reservada))
            balance.quantidade_atual = 12
            person_id, identity = await _identity(session, ctx[0], ctx[1])
            operation_id = await _create_operation(session, ctx, "fechamento")
            divergence_operation_id = await _create_operation(session, ctx, "divergência")
            operation_ids.extend([operation_id, divergence_operation_id])
            request_id, item_id = await _create_request(
                session, ctx, person_id, 2, "CONSUMIVEL", operation_id
            )
            divergence_request_id, divergence_item_id = await _create_request(
                session, ctx, person_id, 10, "CONSUMIVEL", divergence_operation_id
            )
            request_ids.extend([request_id, divergence_request_id])
            await session.commit()

        delivery_id, _ = await _deliver(factory, ctx, request_id, item_id, ctx[1], 2)
        device_id, _ = await _receive(factory, ctx, request_id, item_id, delivery_id, ctx[1], 2)
        async with factory() as session:
            await _tenant_context(session, ctx[0])
            with pytest.raises(BusinessRuleError, match="não conciliada|posse"):
                await OperacaoService(session, ctx[0]).atualizar(
                    operation_id, OperacaoAgricolaUpdate(status="REALIZADA")
                )
            await session.rollback()
            assert (await session.get(OperacaoAgricola, operation_id)).status == "PLANEJADA"

        async with factory() as session:
            await _tenant_context(session, ctx[0])
            request = await session.get(RequisicaoMaterial, request_id)
            returned = await RequisicaoPosseService(session, ctx[0]).destinar(
                request_id,
                DestinacaoRequisicaoRequest(
                    item_id=item_id,
                    entrega_evento_id=delivery_id,
                    tipo_evento="DEVOLUCAO",
                    quantidade=2,
                    base_version=request.version,
                    client_operation_id=f"01F1-CLOSE-RETURN-{request_id}",
                    deposito_id=ctx[4],
                    dispositivo_id=device_id,
                ),
                usuario_id=ctx[1],
                dispositivo_id=device_id,
            )
            await session.commit()
            assert returned.projection.itens[0].status_conciliacao == "CONCILIADO"

        async with factory() as session:
            await _tenant_context(session, ctx[0])
            closed = await OperacaoService(session, ctx[0]).atualizar(
                operation_id, OperacaoAgricolaUpdate(status="REALIZADA")
            )
            assert closed.status == "REALIZADA"
            await session.rollback()

        divergence_delivery_id, _ = await _deliver(
            factory, ctx, divergence_request_id, divergence_item_id, ctx[1], 10
        )
        _, divergence_receipt = await _receive(
            factory,
            ctx,
            divergence_request_id,
            divergence_item_id,
            divergence_delivery_id,
            ctx[1],
            8,
            result="DIVERGENTE",
            reason="duas unidades não chegaram",
        )
        assert divergence_receipt.projection.itens[0].status_conferencia == "DIVERGENTE"
        async with factory() as session:
            await _tenant_context(session, ctx[0])
            with pytest.raises(BusinessRuleError):
                await OperacaoService(session, ctx[0]).atualizar(
                    divergence_operation_id, OperacaoAgricolaUpdate(status="REALIZADA")
                )
            await session.rollback()
            assert (
                await session.get(OperacaoAgricola, divergence_operation_id)
            ).status == "PLANEJADA"
    finally:
        if ctx is not None:
            await _cleanup(factory, ctx, request_ids, operation_ids, identity)
        await engine.dispose()
