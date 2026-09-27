"""Prova PostgreSQL real do recebimento Campo 01E.

Executar somente no banco de desenvolvimento controlado:

    DEEPFARMS_RUN_REAL_01E=1 pytest -q \
      tests/integration/operacional/test_requisicao_recebimento_01e_integration.py
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.cadastros.models import ProdutoCatalogo
from core.cadastros.produtos.models import ProdutoEstoque
from core.cadastros.pessoas.models import Pessoa, PessoaUsuario
from core.exceptions import EntityNotFoundError
from core.models.auth import TenantUsuario, Usuario
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from operacional.models.estoque import (
    Deposito,
    EstoqueMovimento,
    ItemRequisicao,
    RequisicaoItemEvento,
    RequisicaoMaterial,
    SaldoEstoque,
)
from operacional.schemas.estoque import (
    RecebimentoRequisicaoRequest,
    RequisicaoItemOperacaoCanonicaRequest,
    ReservaItemCanonicaRequest,
)
from operacional.services.requisicao_canonica_service import RequisicaoCanonicaService
from operacional.services.requisicao_recebimento_service import RequisicaoRecebimentoService


pytestmark = pytest.mark.skipif(
    os.getenv("DEEPFARMS_RUN_REAL_01E") != "1",
    reason="prova PostgreSQL real 01E opt-in",
)


def _engine():
    return create_async_engine(
        os.environ["DATABASE_URL"],
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=False,
        connect_args={"timeout": 30, "ssl": False, "server_settings": {"search_path": "farms"}},
    )


async def _tenant_context(session, tenant_id):
    await session.execute(
        text("select set_config('app.current_tenant_id', :tenant, true)"),
        {"tenant": str(tenant_id)},
    )


async def test_recebimento_offline_sem_nova_baixa_fisica() -> None:
    engine = _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    request_id = item_id = identity_id = person_id = None
    created_identity = False
    tenant_id = balance_id = None
    original_balance = None
    device_id = uuid4()
    try:
        async with factory() as session:
            context = (
                await session.execute(
                    select(
                        Tenant.id,
                        TenantUsuario.usuario_id,
                        UnidadeProdutiva.id,
                        ProdutoCatalogo.id,
                        Deposito.id,
                        SaldoEstoque.id,
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
            assert context is not None, "contexto de teste 01E não encontrado"
            tenant_id, user_id, unit_id, product_id, depot_id, balance_id = context
            await _tenant_context(session, tenant_id)

            identity = (
                await session.execute(
                    select(PessoaUsuario).where(
                        PessoaUsuario.tenant_id == tenant_id,
                        PessoaUsuario.usuario_id == user_id,
                        PessoaUsuario.status == "ATIVO",
                    )
                )
            ).scalars().first()
            if identity is None:
                person = Pessoa(
                    tenant_id=tenant_id,
                    tipo="PF",
                    nome_exibicao=f"T01E pessoa {uuid4().hex[:8]}",
                )
                session.add(person)
                await session.flush()
                identity = PessoaUsuario(
                    tenant_id=tenant_id,
                    pessoa_id=person.id,
                    usuario_id=user_id,
                    status="ATIVO",
                    vigencia_inicio=datetime.now(timezone.utc) - timedelta(minutes=1),
                    motivo="fixture temporário 01E",
                )
                session.add(identity)
                await session.flush()
                identity_id, person_id, created_identity = identity.id, person.id, True
            else:
                identity_id, person_id = identity.id, identity.pessoa_id

            balance = await session.get(SaldoEstoque, balance_id, with_for_update=True)
            assert balance is not None
            original_balance = (float(balance.quantidade_atual), float(balance.quantidade_reservada))
            balance.quantidade_atual = 100
            request = RequisicaoMaterial(
                tenant_id=tenant_id,
                numero=f"T01E-{uuid4().hex[:12]}",
                unidade_produtiva_id=unit_id,
                solicitante_id=user_id,
                responsavel_pessoa_id=person_id,
                status="APROVADA",
                origem_tipo="ORDEM_SERVICO",
            )
            session.add(request)
            await session.flush()
            item = ItemRequisicao(
                tenant_id=tenant_id,
                requisicao_id=request.id,
                produto_id=product_id,
                deposito_id=depot_id,
                quantidade_solicitada=100,
                quantidade_aprovada=100,
                natureza_item="CONSUMIVEL",
            )
            session.add(item)
            await session.flush()
            request_id, item_id = request.id, item.id
            await session.commit()

        async with factory() as session:
            await _tenant_context(session, tenant_id)
            canonical = RequisicaoCanonicaService(session, tenant_id)
            await canonical.reservar_item(
                request_id,
                item_id,
                ReservaItemCanonicaRequest(
                    quantidade=100,
                    deposito_id=depot_id,
                    client_operation_id=f"T01E-RESERVE-{request_id}",
                ),
                user_id,
            )
            await canonical.separar_item(
                request_id,
                item_id,
                RequisicaoItemOperacaoCanonicaRequest(
                    quantidade=100,
                    deposito_id=depot_id,
                    client_operation_id=f"T01E-PICK-{request_id}",
                ),
                user_id,
            )
            delivery, movement = await canonical.entregar_item(
                request_id,
                item_id,
                RequisicaoItemOperacaoCanonicaRequest(
                    quantidade=100,
                    deposito_id=depot_id,
                    client_operation_id=f"T01E-DELIVERY-{request_id}",
                ),
                user_id,
            )
            await session.commit()
            delivery_id = delivery.id
            movement_id = movement.id

        command = RecebimentoRequisicaoRequest(
            item_id=item_id,
            entrega_evento_id=delivery_id,
            quantidade_recebida=92,
            resultado="DIVERGENTE",
            base_version=4,
            client_operation_id=f"T01E-RECEIPT-{request_id}",
            dispositivo_id=device_id,
            motivo="8 kg não conferidos na entrega",
        )
        async with factory() as session:
            await _tenant_context(session, tenant_id)
            before_balance = await session.get(SaldoEstoque, balance_id)
            before_movement_count = (
                await session.execute(
                    select(func.count()).select_from(EstoqueMovimento).where(
                        EstoqueMovimento.requisicao_item_evento_id == delivery_id
                    )
                )
            ).scalar_one()
            ack = await RequisicaoRecebimentoService(session, tenant_id).receber(
                request_id,
                command,
                usuario_id=user_id,
                dispositivo_id=device_id,
            )
            await session.commit()
            assert ack.resultado == "DIVERGENTE"
            assert ack.projection.itens[0].quantidade_recebida == 92
            assert ack.projection.itens[0].quantidade_pendente_conferencia == 8
            assert ack.projection.itens[0].quantidade_em_posse == 92
            assert float(before_balance.quantidade_atual) == 0
            assert before_movement_count == 1

        async with factory() as session:
            await _tenant_context(session, tenant_id)
            retry = await RequisicaoRecebimentoService(session, tenant_id).receber(
                request_id,
                command,
                usuario_id=user_id,
                dispositivo_id=device_id,
            )
            await session.commit()
            assert retry.evento_id == ack.evento_id
            await _tenant_context(session, tenant_id)

            receipt_count = (
                await session.execute(
                    select(func.count()).select_from(RequisicaoItemEvento).where(
                        RequisicaoItemEvento.requisicao_id == request_id,
                        RequisicaoItemEvento.tipo_evento == "RECEBIMENTO",
                    )
                )
            ).scalar_one()
            movement_count = (
                await session.execute(
                    select(func.count()).select_from(EstoqueMovimento).where(
                        EstoqueMovimento.requisicao_item_evento_id == delivery_id
                    )
                )
            ).scalar_one()
            balance_after = await session.get(SaldoEstoque, balance_id)
            assert receipt_count == 1
            assert movement_count == 1
            assert float(balance_after.quantidade_atual) == 0
            assert await session.get(EstoqueMovimento, movement_id) is not None

            other_context = (
                await session.execute(
                    select(Tenant.id, TenantUsuario.usuario_id)
                    .join(TenantUsuario, TenantUsuario.tenant_id == Tenant.id)
                    .where(
                        Tenant.id != tenant_id,
                        Tenant.ativo.is_(True),
                        TenantUsuario.status == "ATIVO",
                    )
                    .limit(1)
                )
            ).first()
            assert other_context is not None, "Tenant B não encontrado para prova 01E"
            other_tenant_id, other_user_id = other_context
            await _tenant_context(session, other_tenant_id)
            with pytest.raises(EntityNotFoundError):
                await RequisicaoRecebimentoService(session, other_tenant_id).receber(
                    request_id,
                    command,
                    usuario_id=other_user_id,
                    dispositivo_id=device_id,
                )
            await session.rollback()
            await _tenant_context(session, tenant_id)
            assert (
                await session.execute(
                    select(func.count()).select_from(RequisicaoItemEvento).where(
                        RequisicaoItemEvento.requisicao_id == request_id,
                        RequisicaoItemEvento.tipo_evento == "RECEBIMENTO",
                    )
                )
            ).scalar_one() == 1
    finally:
        if tenant_id is not None:
            async with factory() as session:
                await _tenant_context(session, tenant_id)
                if request_id is not None:
                    await session.execute(
                        text("alter table farms.estoque_requisicao_item_eventos disable trigger trg_estoque_requisicao_item_evento_append_only")
                    )
                    await session.execute(
                        text("alter table farms.estoque_movimentos disable trigger tg_estoque_movimentos_append_only")
                    )
                    await session.execute(
                        text("delete from farms.estoque_movimentos where requisicao_item_evento_id in (select id from farms.estoque_requisicao_item_eventos where requisicao_id=:id)"),
                        {"id": str(request_id)},
                    )
                    await session.execute(
                        text("delete from farms.domain_event_outbox where source_id in (select id::text from farms.estoque_requisicao_item_eventos where requisicao_id=:id)"),
                        {"id": str(request_id)},
                    )
                    await session.execute(
                        text("delete from farms.estoque_requisicao_item_eventos where requisicao_id=:id"),
                        {"id": str(request_id)},
                    )
                    await session.execute(
                        text("delete from farms.estoque_reservas where item_requisicao_id=:id"),
                        {"id": str(item_id)},
                    )
                    await session.execute(
                        text("delete from farms.estoque_requisicoes_itens where id=:id"),
                        {"id": str(item_id)},
                    )
                    await session.execute(
                        text("delete from farms.estoque_requisicoes where id=:id"),
                        {"id": str(request_id)},
                    )
                    await session.execute(
                        text("alter table farms.estoque_requisicao_item_eventos enable trigger trg_estoque_requisicao_item_evento_append_only")
                    )
                    await session.execute(
                        text("alter table farms.estoque_movimentos enable trigger tg_estoque_movimentos_append_only")
                    )
                balance = await session.get(SaldoEstoque, balance_id, with_for_update=True)
                if balance is not None and original_balance is not None:
                    balance.quantidade_atual, balance.quantidade_reservada = original_balance
                if created_identity and identity_id is not None:
                    await session.execute(
                        text("delete from farms.cadastros_pessoas_usuarios where id=:id"),
                        {"id": str(identity_id)},
                    )
                    await session.execute(
                        text("delete from farms.cadastros_pessoas where id=:id"),
                        {"id": str(person_id)},
                    )
                await session.commit()
        await engine.dispose()
