"""Fluxo canônico 01D: reserva, separação e entrega física.

Este serviço é deliberadamente separado do workflow legado de requisições. A
rota canônica grava o fato operacional e o movimento físico na mesma
transação; o legado continua disponível durante a transição.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError, EntityNotFoundError, TenantViolationError
from core.cadastros.models import ProdutoCatalogo
from core.operational_context import validate_deposito_context, validate_lote_context
from events import DomainEvent, DomainEventOutboxService
from operacional.domain.requisicao_material import TipoRequisicaoItemEvento
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
    RequisicaoItemOperacaoCanonicaRequest,
    ReservaItemCanonicaRequest,
)
from operacional.services.estoque_ledger import registrar_ledger_estoque


ACTIVE_RESERVATION_STATUSES = ("ATIVA", "PARCIALMENTE_CONSUMIDA")


class RequisicaoCanonicaService:
    """Comandos transacionais do 01D, sem recebimento ou consumo."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _lock_context(self, req_id: UUID, item_id: UUID) -> tuple[RequisicaoMaterial, ItemRequisicao]:
        stmt = (
            select(RequisicaoMaterial, ItemRequisicao)
            .join(ItemRequisicao, ItemRequisicao.requisicao_id == RequisicaoMaterial.id)
            .where(
                RequisicaoMaterial.id == req_id,
                RequisicaoMaterial.tenant_id == self.tenant_id,
                ItemRequisicao.id == item_id,
                ItemRequisicao.tenant_id == self.tenant_id,
            )
            .with_for_update()
        )
        row = (await self.session.execute(stmt)).first()
        if not row:
            raise EntityNotFoundError("Requisição ou item não pertence ao tenant atual.")
        return row

    async def _find_idempotent(self, client_operation_id: str | None) -> RequisicaoItemEvento | None:
        if not client_operation_id:
            return None
        stmt = select(RequisicaoItemEvento).where(
            RequisicaoItemEvento.tenant_id == self.tenant_id,
            RequisicaoItemEvento.client_operation_id == client_operation_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    @staticmethod
    def _validate_retry(
        event: RequisicaoItemEvento,
        *,
        item_id: UUID,
        tipo: str,
        quantidade: float,
        deposito_id: UUID | None,
        lote_id: UUID | None,
    ) -> None:
        if (
            event.item_requisicao_id != item_id
            or event.tipo_evento != tipo
            or Decimal(str(event.quantidade)) != Decimal(str(quantidade))
            or (deposito_id is not None and event.deposito_id != deposito_id)
            or event.lote_id != lote_id
        ):
            raise BusinessRuleError("client_operation_id já identifica outro comando canônico.")

    async def _lock_saldo(self, deposito_id: UUID, produto_id: UUID) -> SaldoEstoque:
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=deposito_id)
        stmt = (
            select(SaldoEstoque)
            .join(Deposito, Deposito.id == SaldoEstoque.deposito_id)
            .where(
                SaldoEstoque.deposito_id == deposito_id,
                SaldoEstoque.produto_id == produto_id,
                Deposito.tenant_id == self.tenant_id,
            )
            .with_for_update()
        )
        saldo = (await self.session.execute(stmt)).scalars().first()
        if not saldo:
            raise BusinessRuleError("Saldo não encontrado para o depósito selecionado.")
        return saldo

    async def _lock_reservas(
        self, item: ItemRequisicao, deposito_id: UUID
    ) -> list[ReservaEstoque]:
        stmt = (
            select(ReservaEstoque)
            .where(
                ReservaEstoque.tenant_id == self.tenant_id,
                ReservaEstoque.item_requisicao_id == item.id,
                ReservaEstoque.produto_id == item.produto_id,
                ReservaEstoque.deposito_id == deposito_id,
                ReservaEstoque.status.in_(ACTIVE_RESERVATION_STATUSES),
            )
            .order_by(ReservaEstoque.created_at.asc(), ReservaEstoque.id.asc())
            .with_for_update()
        )
        return list((await self.session.execute(stmt)).scalars().all())

    @staticmethod
    def _reserva_restante(reserva: ReservaEstoque) -> float:
        return max(0.0, float(reserva.quantidade) - float(reserva.quantidade_consumida or 0.0))

    async def reservar_item(
        self, req_id: UUID, item_id: UUID, data: ReservaItemCanonicaRequest, usuario_id: UUID
    ) -> ReservaEstoque:
        existing = await self._find_reserva_by_client_operation(data.client_operation_id)
        if existing:
            if (
                existing.item_requisicao_id != item_id
                or float(existing.quantidade) != float(data.quantidade)
                or existing.deposito_id != data.deposito_id
            ):
                raise BusinessRuleError("client_operation_id já identifica outra reserva.")
            return existing

        req, item = await self._lock_context(req_id, item_id)
        self._validate_mutable_request(req)
        self._validate_version(req, data.base_version)
        aprovado = float(item.quantidade_aprovada or 0.0)
        if aprovado <= 0:
            raise BusinessRuleError("O item precisa estar aprovado antes da reserva.")
        if data.quantidade > aprovado:
            raise BusinessRuleError("Quantidade reservada não pode exceder a quantidade aprovada.")
        await validate_deposito_context(
            self.session,
            tenant_id=self.tenant_id,
            deposito_id=data.deposito_id,
            expected_unidade_produtiva_id=req.unidade_produtiva_id,
        )
        saldo = await self._lock_saldo(data.deposito_id, item.produto_id)
        reservas = await self._lock_reservas(item, data.deposito_id)
        reservado_do_item = sum(self._reserva_restante(r) for r in reservas)
        if reservado_do_item + data.quantidade > aprovado:
            raise BusinessRuleError("A quantidade reservada excederia a aprovação do item.")
        disponivel = float(saldo.quantidade_atual) - float(saldo.quantidade_reservada)
        if disponivel < data.quantidade:
            raise BusinessRuleError(
                f"Saldo disponível insuficiente para reserva. Disponível: {disponivel:.3f}, "
                f"solicitado: {data.quantidade:.3f}"
            )

        reserva = ReservaEstoque(
            tenant_id=self.tenant_id,
            produto_id=item.produto_id,
            deposito_id=data.deposito_id,
            criado_por_id=usuario_id,
            item_requisicao_id=item.id,
            quantidade=data.quantidade,
            quantidade_consumida=0,
            motivo=data.motivo or f"Requisição canônica {req.id}",
            referencia_tipo="REQUISICAO",
            referencia_id=req.id,
            status="ATIVA",
            client_operation_id=data.client_operation_id,
        )
        saldo.quantidade_reservada = float(saldo.quantidade_reservada) + data.quantidade
        self.session.add(reserva)
        req.version += 1
        await self.session.flush()
        return reserva

    async def _find_reserva_by_client_operation(self, key: str | None) -> ReservaEstoque | None:
        if not key:
            return None
        stmt = select(ReservaEstoque).where(
            ReservaEstoque.tenant_id == self.tenant_id,
            ReservaEstoque.client_operation_id == key,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def separar_item(
        self,
        req_id: UUID,
        item_id: UUID,
        data: RequisicaoItemOperacaoCanonicaRequest,
        usuario_id: UUID,
    ) -> RequisicaoItemEvento:
        existing = await self._find_idempotent(data.client_operation_id)
        if existing:
            self._validate_retry(
                existing,
                item_id=item_id,
                tipo=TipoRequisicaoItemEvento.SEPARACAO.value,
                quantidade=data.quantidade,
                deposito_id=data.deposito_id,
                lote_id=data.lote_id,
            )
            return existing
        req, item = await self._lock_context(req_id, item_id)
        existing = await self._find_idempotent(data.client_operation_id)
        if existing:
            self._validate_retry(
                existing,
                item_id=item_id,
                tipo=TipoRequisicaoItemEvento.SEPARACAO.value,
                quantidade=data.quantidade,
                deposito_id=data.deposito_id,
                lote_id=data.lote_id,
            )
            return existing
        self._validate_mutable_request(req)
        self._validate_version(req, data.base_version)
        deposito_id = data.deposito_id or item.deposito_id
        if not deposito_id:
            raise BusinessRuleError("O item precisa de depósito para separação.")
        reservas = await self._lock_reservas(item, deposito_id)
        if sum(self._reserva_restante(r) for r in reservas) < data.quantidade:
            raise BusinessRuleError("Não há reserva ativa suficiente para separar este item.")
        await self._validate_lote(item, deposito_id, data.lote_id, data.quantidade)
        produto = await self._produto(item.produto_id)
        aprovado = float(item.quantidade_aprovada or 0.0)
        separado = await self._sum_events(item.id, TipoRequisicaoItemEvento.SEPARACAO.value)
        if separado + data.quantidade > aprovado:
            raise BusinessRuleError("Quantidade separada não pode exceder a aprovada.")
        event = self._build_event(
            req=req,
            item=item,
            tipo=TipoRequisicaoItemEvento.SEPARACAO.value,
            quantidade=data.quantidade,
            deposito_id=deposito_id,
            lote_id=data.lote_id,
            usuario_id=usuario_id,
            unidade=produto.unidade_medida,
            client_operation_id=data.client_operation_id,
            ocorrido_em_dispositivo=data.ocorrido_em_dispositivo,
            motivo=data.motivo,
        )
        self.session.add(event)
        req.version += 1
        event.versao_requisicao = req.version
        req.status = "SEPARANDO"
        await self.session.flush()
        await self._enqueue(event, req.unidade_produtiva_id, "operational.material_request.item_separated")
        return event

    async def entregar_item(
        self,
        req_id: UUID,
        item_id: UUID,
        data: RequisicaoItemOperacaoCanonicaRequest,
        usuario_id: UUID,
    ) -> tuple[RequisicaoItemEvento, EstoqueMovimento]:
        existing = await self._find_idempotent(data.client_operation_id)
        if existing:
            self._validate_retry(
                existing,
                item_id=item_id,
                tipo=TipoRequisicaoItemEvento.ENTREGA.value,
                quantidade=data.quantidade,
                deposito_id=data.deposito_id,
                lote_id=data.lote_id,
            )
            movement = await self._movement_for_event(existing.id)
            if movement is None:
                raise BusinessRuleError("Evento de entrega sem movimento físico; transação inconsistente.")
            return existing, movement

        req, item = await self._lock_context(req_id, item_id)
        existing = await self._find_idempotent(data.client_operation_id)
        if existing:
            self._validate_retry(
                existing,
                item_id=item_id,
                tipo=TipoRequisicaoItemEvento.ENTREGA.value,
                quantidade=data.quantidade,
                deposito_id=data.deposito_id,
                lote_id=data.lote_id,
            )
            movement = await self._movement_for_event(existing.id)
            if movement is None:
                raise BusinessRuleError("Evento de entrega sem movimento físico; transação inconsistente.")
            return existing, movement

        self._validate_mutable_request(req)
        self._validate_version(req, data.base_version)
        deposito_id = data.deposito_id or item.deposito_id
        if not deposito_id:
            raise BusinessRuleError("O item precisa de depósito para entrega.")
        if req.status not in ("APROVADA", "SEPARANDO", "SEPARADA"):
            raise BusinessRuleError(f"Requisição não pode ser entregue no status '{req.status}'.")
        reservas = await self._lock_reservas(item, deposito_id)
        reserva_restante = sum(self._reserva_restante(r) for r in reservas)
        if reserva_restante < data.quantidade:
            raise BusinessRuleError("Não há reserva ativa suficiente para a entrega.")
        await self._validate_lote(item, deposito_id, data.lote_id, data.quantidade)
        separado_total = await self._sum_events(item.id, TipoRequisicaoItemEvento.SEPARACAO.value)
        entregue_total = await self._sum_events(item.id, TipoRequisicaoItemEvento.ENTREGA.value)
        separado_lote = await self._sum_events(
            item.id, TipoRequisicaoItemEvento.SEPARACAO.value, lote_id=data.lote_id, deposito_id=deposito_id
        )
        entregue_lote = await self._sum_events(
            item.id, TipoRequisicaoItemEvento.ENTREGA.value, lote_id=data.lote_id, deposito_id=deposito_id
        )
        aprovado = float(item.quantidade_aprovada or 0.0)
        if entregue_total + data.quantidade > aprovado:
            raise BusinessRuleError("Quantidade entregue não pode exceder a aprovada.")
        if entregue_total + data.quantidade > separado_total:
            raise BusinessRuleError("Quantidade entregue não pode exceder a separada.")
        if separado_lote - entregue_lote < data.quantidade:
            raise BusinessRuleError("A quantidade/lote entregue não foi previamente separado.")

        saldo = await self._lock_saldo(deposito_id, item.produto_id)
        total_reservado = await self._sum_active_reservations(item.produto_id, deposito_id)
        reservado_do_item = reserva_restante
        disponivel_para_este_item = float(saldo.quantidade_atual) - max(
            0.0, total_reservado - reservado_do_item
        )
        if disponivel_para_este_item < data.quantidade:
            raise BusinessRuleError(
                f"Saldo físico insuficiente para entrega. Disponível para esta reserva: "
                f"{disponivel_para_este_item:.3f}, necessário: {data.quantidade:.3f}"
            )

        produto = await self._produto(item.produto_id)
        await self._validar_receituario(produto, req)
        lote = None
        if data.lote_id:
            lote = (await self.session.execute(
                select(LoteEstoque)
                .join(Deposito, Deposito.id == LoteEstoque.deposito_id)
                .where(
                    LoteEstoque.id == data.lote_id,
                    LoteEstoque.produto_id == item.produto_id,
                    LoteEstoque.deposito_id == deposito_id,
                    Deposito.tenant_id == self.tenant_id,
                )
                .with_for_update()
            )).scalars().first()
            if lote is None:
                raise TenantViolationError(
                    "Lote não pertence ao produto, depósito ou tenant atual.",
                    tenant_id=self.tenant_id,
                    resource="lote",
                )
            if float(lote.quantidade_atual) < data.quantidade:
                raise BusinessRuleError("Saldo insuficiente no lote selecionado.")

        custo_unit = await self._custo_unitario(item.produto_id, deposito_id, data.lote_id)
        event = self._build_event(
            req=req,
            item=item,
            tipo=TipoRequisicaoItemEvento.ENTREGA.value,
            quantidade=data.quantidade,
            deposito_id=deposito_id,
            lote_id=data.lote_id,
            usuario_id=usuario_id,
            unidade=produto.unidade_medida,
            client_operation_id=data.client_operation_id,
            ocorrido_em_dispositivo=data.ocorrido_em_dispositivo,
            motivo=data.motivo or "Handoff físico ao responsável operacional; aguardando conferência.",
        )
        self.session.add(event)
        req.version += 1
        event.versao_requisicao = req.version
        await self.session.flush()

        movimento = await registrar_ledger_estoque(
            self.session,
            tenant_id=self.tenant_id,
            produto_id=item.produto_id,
            deposito_id=deposito_id,
            lote_id=data.lote_id,
            tipo_movimento="SAIDA",
            quantidade=data.quantidade,
            custo_unitario=custo_unit,
            origem="REQUISICAO",
            origem_id=req.id,
            requisicao_item_evento_id=event.id,
            observacoes=data.motivo or f"Entrega canônica da requisição {req.id}",
            custo_medio_anterior=float(saldo.custo_medio) if saldo.custo_medio is not None else None,
            custo_medio_resultante=float(saldo.custo_medio) if saldo.custo_medio is not None else None,
        )
        saldo.quantidade_atual = float(saldo.quantidade_atual) - data.quantidade
        if lote is not None:
            lote.quantidade_atual = float(lote.quantidade_atual) - data.quantidade
            if lote.quantidade_atual <= 0:
                lote.status = "ESGOTADO"
        item.quantidade_entregue = float(item.quantidade_entregue or 0.0) + data.quantidade
        if item.lote_id is None:
            item.lote_id = data.lote_id
        elif item.lote_id != data.lote_id:
            item.lote_id = None
        await self._consume_reservation_quantity(reservas, data.quantidade, saldo)
        await self.session.flush()
        await self._refresh_status(req)
        await self._enqueue(event, req.unidade_produtiva_id, "operational.material_request.delivered")
        return event, movimento

    async def cancelar(self, req_id: UUID, usuario_id: UUID) -> RequisicaoMaterial:
        req = await self._lock_request(req_id)
        entrega_existente = (await self.session.execute(
            select(RequisicaoItemEvento.id).where(
                RequisicaoItemEvento.tenant_id == self.tenant_id,
                RequisicaoItemEvento.requisicao_id == req.id,
                RequisicaoItemEvento.tipo_evento == TipoRequisicaoItemEvento.ENTREGA.value,
            ).limit(1)
        )).scalar_one_or_none()
        if req.status == "ENTREGUE" or entrega_existente is not None:
            raise BusinessRuleError("Requisição com entrega física não pode ser cancelada; use devolução futura.")
        itens = list((await self.session.execute(
            select(ItemRequisicao).where(
                ItemRequisicao.tenant_id == self.tenant_id,
                ItemRequisicao.requisicao_id == req.id,
            )
        )).scalars().all())
        for item in itens:
            deps = list((await self.session.execute(
                select(ReservaEstoque).where(
                    ReservaEstoque.tenant_id == self.tenant_id,
                    ReservaEstoque.item_requisicao_id == item.id,
                    ReservaEstoque.status.in_(ACTIVE_RESERVATION_STATUSES),
                ).with_for_update()
            )).scalars().all())
            for reserva in deps:
                saldo = await self._lock_saldo(reserva.deposito_id, reserva.produto_id)
                restante = self._reserva_restante(reserva)
                saldo.quantidade_reservada = max(0.0, float(saldo.quantidade_reservada) - restante)
                reserva.status = "LIBERADA"
        req.status = "CANCELADA"
        req.version += 1
        await self.session.flush()
        return req

    async def _lock_request(self, req_id: UUID) -> RequisicaoMaterial:
        req = (await self.session.execute(
            select(RequisicaoMaterial).where(
                RequisicaoMaterial.id == req_id,
                RequisicaoMaterial.tenant_id == self.tenant_id,
            ).with_for_update()
        )).scalars().first()
        if not req:
            raise EntityNotFoundError("Requisição não encontrada no tenant atual.")
        return req

    async def _sum_events(
        self,
        item_id: UUID,
        tipo: str,
        *,
        lote_id: UUID | None = None,
        deposito_id: UUID | None = None,
    ) -> float:
        stmt = select(func.coalesce(func.sum(RequisicaoItemEvento.quantidade), 0)).where(
            RequisicaoItemEvento.tenant_id == self.tenant_id,
            RequisicaoItemEvento.item_requisicao_id == item_id,
            RequisicaoItemEvento.tipo_evento == tipo,
        )
        if lote_id is not None:
            stmt = stmt.where(RequisicaoItemEvento.lote_id == lote_id)
        if deposito_id is not None:
            stmt = stmt.where(RequisicaoItemEvento.deposito_id == deposito_id)
        return float((await self.session.execute(stmt)).scalar_one() or 0)

    async def _sum_active_reservations(self, produto_id: UUID, deposito_id: UUID) -> float:
        stmt = select(func.coalesce(func.sum(ReservaEstoque.quantidade - ReservaEstoque.quantidade_consumida), 0)).where(
            ReservaEstoque.tenant_id == self.tenant_id,
            ReservaEstoque.produto_id == produto_id,
            ReservaEstoque.deposito_id == deposito_id,
            ReservaEstoque.status.in_(ACTIVE_RESERVATION_STATUSES),
        )
        return float((await self.session.execute(stmt)).scalar_one() or 0)

    async def _validate_lote(self, item: ItemRequisicao, deposito_id: UUID, lote_id: UUID | None, quantidade: float) -> None:
        if lote_id is None:
            return
        lote = await validate_lote_context(
            self.session,
            tenant_id=self.tenant_id,
            lote_id=lote_id,
            produto_id=item.produto_id,
            deposito_id=deposito_id,
        )
        if float(lote.quantidade_atual) < quantidade:
            raise BusinessRuleError("Saldo insuficiente no lote selecionado.")

    async def _consume_reservation_quantity(
        self, reservas: list[ReservaEstoque], quantidade: float, saldo: SaldoEstoque
    ) -> None:
        restante = quantidade
        for reserva in reservas:
            if restante <= 0:
                break
            disponivel = self._reserva_restante(reserva)
            usado = min(disponivel, restante)
            reserva.quantidade_consumida = float(reserva.quantidade_consumida or 0.0) + usado
            restante -= usado
            reserva.status = "CONSUMIDA" if self._reserva_restante(reserva) <= 1e-9 else "PARCIALMENTE_CONSUMIDA"
            saldo.quantidade_reservada = max(0.0, float(saldo.quantidade_reservada) - usado)
        if restante > 1e-9:
            raise BusinessRuleError("Reserva insuficiente para consumir durante a entrega.")

    async def _movement_for_event(self, event_id: UUID) -> EstoqueMovimento | None:
        return (await self.session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.tenant_id == self.tenant_id,
                EstoqueMovimento.requisicao_item_evento_id == event_id,
            )
        )).scalars().first()

    async def _produto(self, produto_id: UUID) -> ProdutoCatalogo:
        produto = (await self.session.execute(
            select(ProdutoCatalogo).where(
                ProdutoCatalogo.id == produto_id,
                or_(ProdutoCatalogo.tenant_id.is_(None), ProdutoCatalogo.tenant_id == self.tenant_id),
            )
        )).scalars().first()
        if not produto:
            raise TenantViolationError("Produto não pertence ao tenant atual.", tenant_id=self.tenant_id, resource="produto")
        return produto

    async def _custo_unitario(self, produto_id: UUID, deposito_id: UUID, lote_id: UUID | None) -> float | None:
        if lote_id:
            lote = await validate_lote_context(self.session, tenant_id=self.tenant_id, lote_id=lote_id)
            if lote.custo_unitario is not None:
                return float(lote.custo_unitario)
        saldo = await self._lock_saldo(deposito_id, produto_id)
        return float(saldo.custo_medio) if saldo.custo_medio is not None else None

    async def _validar_receituario(self, produto: ProdutoCatalogo, req: RequisicaoMaterial) -> None:
        # A regra regulatória existente fica centralizada no serviço legado;
        # importar aqui evita duplicar a política de receituário.
        from operacional.services.estoque_service import EstoqueService

        await EstoqueService(self.session, self.tenant_id)._validar_receituario_obrigatorio(
            produto.id, safra_id=req.safra_id, operacao_id=req.operacao_agricola_id
        )

    @staticmethod
    def _validate_mutable_request(req: RequisicaoMaterial) -> None:
        if req.compatibilidade_legado is not None:
            raise BusinessRuleError("Requisição legada não pode entrar no fluxo canônico sem cutover explícito.")
        if req.status in ("CANCELADA", "RECUSADA", "ENTREGUE"):
            raise BusinessRuleError(f"Requisição não pode ser alterada no status '{req.status}'.")

    @staticmethod
    def _validate_version(req: RequisicaoMaterial, base_version: int | None) -> None:
        if base_version is not None and base_version != req.version:
            raise BusinessRuleError("Versão da requisição obsoleta; recarregue o contexto.")

    @staticmethod
    def _build_event(
        *,
        req: RequisicaoMaterial,
        item: ItemRequisicao,
        tipo: str,
        quantidade: float,
        deposito_id: UUID,
        lote_id: UUID | None,
        usuario_id: UUID,
        unidade: str,
        client_operation_id: str,
        ocorrido_em_dispositivo,
        motivo: str | None,
    ) -> RequisicaoItemEvento:
        return RequisicaoItemEvento(
            tenant_id=req.tenant_id,
            requisicao_id=req.id,
            item_requisicao_id=item.id,
            tipo_evento=tipo,
            quantidade=quantidade,
            unidade=unidade,
            produto_id=item.produto_id,
            lote_id=lote_id,
            deposito_id=deposito_id,
            operacao_agricola_id=req.operacao_agricola_id,
            usuario_id=usuario_id,
            pessoa_operacional_id=req.responsavel_pessoa_id,
            ocorrido_em_dispositivo=ocorrido_em_dispositivo,
            motivo=motivo,
            versao_requisicao=req.version + 1,
            correlation_id=uuid4(),
            client_operation_id=client_operation_id,
            provenance="CANONICAL",
        )

    async def _refresh_status(self, req: RequisicaoMaterial) -> None:
        items = list((await self.session.execute(
            select(ItemRequisicao).where(
                ItemRequisicao.tenant_id == self.tenant_id,
                ItemRequisicao.requisicao_id == req.id,
            )
        )).scalars().all())
        if not items:
            return
        all_delivered = True
        all_separated = True
        for item in items:
            approved = float(item.quantidade_aprovada or 0)
            separated = await self._sum_events(item.id, TipoRequisicaoItemEvento.SEPARACAO.value)
            delivered = await self._sum_events(item.id, TipoRequisicaoItemEvento.ENTREGA.value)
            all_delivered &= approved > 0 and delivered >= approved
            all_separated &= approved > 0 and separated >= approved
        if all_delivered:
            req.status = "ENTREGUE"
        elif all_separated:
            req.status = "SEPARADA"
        else:
            req.status = "SEPARANDO"

    async def _enqueue(self, event: RequisicaoItemEvento, unidade_id: UUID, event_type: str) -> None:
        await DomainEventOutboxService(self.session, self.tenant_id).enqueue(
            DomainEvent(
                tenant_id=self.tenant_id,
                unidade_produtiva_id=unidade_id,
                domain="operacional",
                event_type=event_type,
                source_type="RequisicaoItemEvento",
                entity_type="RequisicaoItemEvento",
                entity_id=event.id,
                correlation_id=event.correlation_id,
                metadata={
                    "requisicao_id": str(event.requisicao_id),
                    "item_requisicao_id": str(event.item_requisicao_id),
                    "quantidade": float(event.quantidade),
                    "client_operation_id": event.client_operation_id,
                },
            ),
            commit=False,
        )
