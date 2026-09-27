"""Destinação canônica da posse material após o recebimento (01F).

Entrega é a única saída física. Consumo, perda, dano e extravio são fatos
operacionais; somente devolução cria uma entrada física, sempre vinculada ao
evento de devolução e à entrega exata que originou a posse.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.operational_context import validate_deposito_context, validate_lote_context
from events import DomainEvent, DomainEventOutboxService
from operacional.domain.requisicao_material import NaturezaItem, TipoRequisicaoItemEvento
from operacional.models.estoque import (
    Deposito,
    EstoqueMovimento,
    ItemRequisicao,
    LoteEstoque,
    RequisicaoItemEvento,
    RequisicaoMaterial,
    SaldoEstoque,
)
from operacional.schemas.estoque import (
    DestinacaoCampoAck,
    DestinacaoRequisicaoRequest,
)
from operacional.services.estoque_ledger import registrar_ledger_estoque
from operacional.services.identidade_operacional_service import IdentidadeOperacionalService
from operacional.services.requisicao_recebimento_service import RequisicaoRecebimentoService


DISPOSITION_TYPES = {
    TipoRequisicaoItemEvento.CONSUMO.value,
    TipoRequisicaoItemEvento.DEVOLUCAO.value,
    TipoRequisicaoItemEvento.PERDA.value,
    TipoRequisicaoItemEvento.DANO.value,
    TipoRequisicaoItemEvento.EXTRAVIO.value,
}
RETURN_TYPE = TipoRequisicaoItemEvento.DEVOLUCAO.value


def _number(value: Decimal | float | int | None) -> float:
    return float(value or 0)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RequisicaoPosseService:
    """Registra consumo, retorno e perdas sobre posse operacional recebida."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def destinar(
        self,
        requisicao_id: UUID,
        data: DestinacaoRequisicaoRequest,
        *,
        usuario_id: UUID,
        dispositivo_id: UUID,
    ) -> DestinacaoCampoAck:
        """Aplica uma destinação idempotente e transacional à posse.

        Raises:
            EntityNotFoundError: quando a origem não pertence ao tenant.
            BusinessRuleError: quando a posse, versão ou autorização é inválida.
        """
        requisicao, item = await self._lock_request_item(requisicao_id, data.item_id)
        identidade = await IdentidadeOperacionalService.validar_recebedor(
            self.session, self.tenant_id, requisicao_id, usuario_id
        )
        existing = await self._find_idempotent(data.client_operation_id)
        if existing is not None:
            self._validate_retry(existing, data, requisicao_id, usuario_id)
            projection = await self._projection(requisicao)
            movement_id = await self._movement_id(existing.id)
            return self._ack(existing, projection, data.client_operation_id, movement_id)

        self._validate_command(requisicao, data, dispositivo_id)
        entrega = await self._lock_delivery(requisicao_id, item.id, data.entrega_evento_id)
        received = await self._sum_delivery(entrega.id, TipoRequisicaoItemEvento.RECEBIMENTO.value)
        refused = await self._sum_delivery(entrega.id, TipoRequisicaoItemEvento.RECUSA.value)
        if received <= 0 or received + refused < _number(entrega.quantidade) - 1e-9:
            raise BusinessRuleError("A entrega ainda possui conferência ou divergência pendente.")
        disposition = await self._disposition_totals(entrega.id)
        possession = received - sum(disposition.values())
        if possession < -1e-9:
            raise BusinessRuleError("A posse canônica já está inconsistente.")
        if float(data.quantidade) > possession + 1e-9:
            raise BusinessRuleError("Quantidade superior à posse operacional disponível.")

        execution = await self._validate_nature_and_execution(requisicao, item, data)
        target_deposit, target_lot, movement = await self._prepare_return(
            requisicao, item, entrega, data
        )
        requisicao.version += 1
        event = self._build_event(
            requisicao,
            item,
            entrega,
            data,
            usuario_id,
            identidade.pessoa_id,
            execution,
        )
        self.session.add(event)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            existing = await self._find_idempotent(data.client_operation_id)
            if existing is None:
                raise
            self._validate_retry(existing, data, requisicao_id, usuario_id)
            requisicao = await self._request_for_event(existing)
            projection = await self._projection(requisicao)
            movement_id = await self._movement_id(existing.id)
            return self._ack(existing, projection, data.client_operation_id, movement_id)
        if data.tipo_evento == RETURN_TYPE:
            movement = await self._record_return_movement(
                event, movement, requisicao, item, entrega, target_deposit, target_lot
            )
        await self._enqueue(event, requisicao, data)
        projection = await self._projection(requisicao)
        return DestinacaoCampoAck(
            evento_id=event.id,
            movimento_id=movement.id if movement is not None else None,
            requisicao_id=requisicao.id,
            item_id=item.id,
            client_operation_id=data.client_operation_id,
            version=requisicao.version,
            tipo_evento=data.tipo_evento,
            projection=projection,
        )

    async def _lock_request_item(self, req_id: UUID, item_id: UUID):
        row = (
            await self.session.execute(
                select(RequisicaoMaterial, ItemRequisicao)
                .join(ItemRequisicao, ItemRequisicao.requisicao_id == RequisicaoMaterial.id)
                .where(
                    RequisicaoMaterial.tenant_id == self.tenant_id,
                    RequisicaoMaterial.id == req_id,
                    ItemRequisicao.tenant_id == self.tenant_id,
                    ItemRequisicao.id == item_id,
                )
                .with_for_update()
            )
        ).first()
        if row is None:
            raise EntityNotFoundError("Requisição ou item não pertence ao tenant atual.")
        return row

    async def _lock_delivery(self, req_id: UUID, item_id: UUID, event_id: UUID):
        event = (
            await self.session.execute(
                select(RequisicaoItemEvento)
                .where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.id == event_id,
                    RequisicaoItemEvento.requisicao_id == req_id,
                    RequisicaoItemEvento.item_requisicao_id == item_id,
                    RequisicaoItemEvento.tipo_evento == TipoRequisicaoItemEvento.ENTREGA.value,
                    RequisicaoItemEvento.provenance == "CANONICAL",
                )
                .with_for_update()
            )
        ).scalars().first()
        if event is None:
            raise EntityNotFoundError("Entrega canônica não encontrada para este item.")
        return event

    async def _find_idempotent(self, key: str) -> RequisicaoItemEvento | None:
        return (
            await self.session.execute(
                select(RequisicaoItemEvento).where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.client_operation_id == key,
                )
            )
        ).scalars().first()

    async def _request_for_event(self, event: RequisicaoItemEvento) -> RequisicaoMaterial:
        request = (
            await self.session.execute(
                select(RequisicaoMaterial).where(
                    RequisicaoMaterial.tenant_id == self.tenant_id,
                    RequisicaoMaterial.id == event.requisicao_id,
                )
            )
        ).scalars().first()
        if request is None:
            raise EntityNotFoundError("Requisição do evento não encontrada.")
        return request

    async def _movement_id(self, event_id: UUID) -> UUID | None:
        return (
            await self.session.execute(
                select(EstoqueMovimento.id).where(
                    EstoqueMovimento.tenant_id == self.tenant_id,
                    EstoqueMovimento.requisicao_item_evento_id == event_id,
                )
            )
        ).scalar_one_or_none()

    @staticmethod
    def _validate_retry(event, data, req_id: UUID, usuario_id: UUID) -> None:
        if (
            event.requisicao_id != req_id
            or event.usuario_id != usuario_id
            or event.item_requisicao_id != data.item_id
            or event.evento_entrega_id != data.entrega_evento_id
            or event.tipo_evento != data.tipo_evento
            or Decimal(str(event.quantidade)) != Decimal(str(data.quantidade))
            or event.operacao_execucao_id != data.operacao_execucao_id
            or event.deposito_id != data.deposito_id
            or event.lote_id != data.lote_id
        ):
            raise BusinessRuleError("client_operation_id já identifica outra destinação.")

    @staticmethod
    def _validate_command(req, data, device_id: UUID) -> None:
        if req.compatibilidade_legado is not None:
            raise BusinessRuleError("Requisição legada não pode usar destinação canônica.")
        if req.status in {"CANCELADA", "RECUSADA"}:
            raise BusinessRuleError("Requisição cancelada ou recusada não pode receber destinação.")
        if data.base_version != req.version:
            raise BusinessRuleError("Versão da requisição obsoleta; sincronize antes de continuar.")
        if data.dispositivo_id != device_id:
            raise BusinessRuleError("O dispositivo do comando não corresponde ao token autenticado.")

    async def _sum_delivery(self, delivery_id: UUID, event_type: str) -> float:
        value = (
            await self.session.execute(
                select(func.coalesce(func.sum(RequisicaoItemEvento.quantidade), 0)).where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.evento_entrega_id == delivery_id,
                    RequisicaoItemEvento.tipo_evento == event_type,
                )
            )
        ).scalar_one()
        return _number(value)

    async def _disposition_totals(self, delivery_id: UUID) -> dict[str, float]:
        rows = (
            await self.session.execute(
                select(RequisicaoItemEvento.tipo_evento, func.sum(RequisicaoItemEvento.quantidade))
                .where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.evento_entrega_id == delivery_id,
                    RequisicaoItemEvento.tipo_evento.in_(DISPOSITION_TYPES),
                )
                .group_by(RequisicaoItemEvento.tipo_evento)
            )
        ).all()
        return {row[0]: _number(row[1]) for row in rows}

    async def _validate_nature_and_execution(self, req, item, data):
        nature = item.natureza_item
        if data.tipo_evento == TipoRequisicaoItemEvento.CONSUMO.value:
            if nature != NaturezaItem.CONSUMIVEL.value:
                raise BusinessRuleError("Item retornável não pode ser consumido.")
            if data.operacao_execucao_id is None:
                raise BusinessRuleError("Consumo exige OperacaoExecucao explícita.")
            return await self._validate_execution(req, data.operacao_execucao_id)
        if data.operacao_execucao_id is not None:
            raise BusinessRuleError("OperacaoExecucao só é permitida para consumo.")
        if data.tipo_evento == TipoRequisicaoItemEvento.PERDA.value and nature != NaturezaItem.CONSUMIVEL.value:
            raise BusinessRuleError("Perda é aplicável a consumível; retornável deve ser danificado ou extraviado.")
        if data.tipo_evento in {"PERDA", "DANO", "EXTRAVIO"} and not (data.motivo or "").strip():
            raise BusinessRuleError("Perda, dano e extravio exigem motivo auditável.")
        return None

    async def _validate_execution(self, req, execution_id: UUID):
        row = (
            await self.session.execute(
                select(OperacaoExecucao, OperacaoAgricola)
                .join(OperacaoAgricola, OperacaoAgricola.id == OperacaoExecucao.operacao_id)
                .where(
                    OperacaoExecucao.id == execution_id,
                    OperacaoExecucao.tenant_id == self.tenant_id,
                    OperacaoAgricola.tenant_id == self.tenant_id,
                    OperacaoAgricola.id == req.operacao_agricola_id,
                    OperacaoExecucao.status != "CANCELADA",
                )
            )
        ).first()
        if row is None:
            raise BusinessRuleError("OperacaoExecucao não pertence à operação da requisição.")
        return row[0]

    async def _prepare_return(self, req, item, delivery, data):
        if data.tipo_evento != RETURN_TYPE:
            return None, None, None
        deposito_id = delivery.deposito_id or data.deposito_id
        if deposito_id is None:
            raise BusinessRuleError("Devolução exige depósito de destino.")
        if delivery.deposito_id and data.deposito_id and delivery.deposito_id != data.deposito_id:
            raise BusinessRuleError("Devolução deve retornar ao depósito da entrega.")
        deposito = await validate_deposito_context(
            self.session,
            tenant_id=self.tenant_id,
            deposito_id=deposito_id,
            expected_unidade_produtiva_id=req.unidade_produtiva_id,
        )
        lote_id = delivery.lote_id or data.lote_id
        if delivery.lote_id and data.lote_id and delivery.lote_id != data.lote_id:
            raise BusinessRuleError("Devolução deve preservar o lote efetivamente entregue.")
        lote = None
        if lote_id:
            lote = await validate_lote_context(
                self.session,
                tenant_id=self.tenant_id,
                lote_id=lote_id,
                produto_id=item.produto_id,
                deposito_id=deposito.id,
                expected_unidade_produtiva_id=req.unidade_produtiva_id,
            )
            lote = (
                await self.session.execute(
                    select(LoteEstoque).where(LoteEstoque.id == lote.id).with_for_update()
                )
            ).scalars().one()
        saldo = (
            await self.session.execute(
                select(SaldoEstoque)
                .join(Deposito, Deposito.id == SaldoEstoque.deposito_id)
                .where(
                    SaldoEstoque.deposito_id == deposito.id,
                    SaldoEstoque.produto_id == item.produto_id,
                    Deposito.tenant_id == self.tenant_id,
                )
                .with_for_update()
            )
        ).scalars().first()
        if saldo is None:
            saldo = SaldoEstoque(
                id=uuid4(), deposito_id=deposito.id, produto_id=item.produto_id,
                quantidade_atual=0, quantidade_reservada=0,
            )
            self.session.add(saldo)
            await self.session.flush()
        return deposito, lote, saldo

    def _build_event(self, req, item, delivery, data, user_id, person_id, execution):
        return RequisicaoItemEvento(
            tenant_id=self.tenant_id,
            requisicao_id=req.id,
            item_requisicao_id=item.id,
            tipo_evento=data.tipo_evento,
            quantidade=data.quantidade,
            unidade=delivery.unidade,
            produto_id=item.produto_id,
            lote_id=delivery.lote_id if data.tipo_evento != RETURN_TYPE else (data.lote_id or delivery.lote_id),
            deposito_id=delivery.deposito_id if data.tipo_evento != RETURN_TYPE else (data.deposito_id or delivery.deposito_id),
            operacao_agricola_id=req.operacao_agricola_id,
            operacao_execucao_id=execution.id if execution is not None else None,
            usuario_id=user_id,
            pessoa_operacional_id=person_id,
            dispositivo_id=data.dispositivo_id,
            ocorrido_em=_now(),
            ocorrido_em_dispositivo=data.ocorrido_em_dispositivo,
            motivo=data.motivo,
            versao_requisicao=req.version,
            correlation_id=uuid4(),
            causation_id=delivery.id,
            evento_entrega_id=delivery.id,
            client_operation_id=data.client_operation_id,
            provenance="CANONICAL",
        )

    async def _record_return_movement(self, event, saldo, req, item, delivery, deposito, lote):
        source = (
            await self.session.execute(
                select(EstoqueMovimento).where(
                    EstoqueMovimento.tenant_id == self.tenant_id,
                    EstoqueMovimento.requisicao_item_evento_id == delivery.id,
                )
            )
        ).scalars().first()
        custo_unitario = _number(source.custo_unitario) if source else _number(lote.custo_unitario if lote else 0)
        quantidade_anterior = _number(saldo.quantidade_atual)
        custo_medio_anterior = _number(saldo.custo_medio)
        saldo.quantidade_atual = quantidade_anterior + _number(event.quantidade)
        saldo.custo_medio = (
            ((quantidade_anterior * custo_medio_anterior) + (_number(event.quantidade) * custo_unitario))
            / saldo.quantidade_atual
            if saldo.quantidade_atual > 0 else custo_medio_anterior
        )
        if lote is not None:
            lote.quantidade_atual = _number(lote.quantidade_atual) + _number(event.quantidade)
            if lote.status == "ESGOTADO":
                lote.status = "ATIVO"
        movement = await registrar_ledger_estoque(
            self.session,
            tenant_id=self.tenant_id,
            produto_id=item.produto_id,
            deposito_id=deposito.id,
            lote_id=lote.id if lote is not None else None,
            tipo_movimento="ENTRADA",
            quantidade=_number(event.quantidade),
            custo_unitario=custo_unitario,
            custo_total=round(_number(event.quantidade) * custo_unitario, 2),
            origem="REQUISICAO",
            origem_id=req.id,
            requisicao_item_evento_id=event.id,
            observacoes=f"Devolução canônica da requisição {req.id}",
            custo_medio_anterior=custo_medio_anterior,
            custo_medio_resultante=_number(saldo.custo_medio),
        )
        return movement

    async def _enqueue(self, event, req, data):
        await DomainEventOutboxService(self.session, self.tenant_id).enqueue(
            DomainEvent(
                tenant_id=self.tenant_id,
                unidade_produtiva_id=req.unidade_produtiva_id,
                domain="operacional",
                event_type=f"operational.material_request.{data.tipo_evento.lower()}",
                source_type="RequisicaoItemEvento",
                entity_type="RequisicaoItemEvento",
                entity_id=event.id,
                correlation_id=event.correlation_id,
                metadata={
                    "requisicao_id": str(req.id),
                    "item_requisicao_id": str(event.item_requisicao_id),
                    "evento_entrega_id": str(event.evento_entrega_id),
                    "quantidade": _number(event.quantidade),
                    "tipo_evento": event.tipo_evento,
                    "client_operation_id": data.client_operation_id,
                },
            ),
            commit=False,
        )

    async def _projection(self, req):
        return await RequisicaoRecebimentoService(
            self.session, self.tenant_id
        )._project_request(req, responsavel_autorizado=True)

    @staticmethod
    def _ack(event, projection, key, movement_id=None):
        return DestinacaoCampoAck(
            evento_id=event.id,
            requisicao_id=event.requisicao_id,
            item_id=event.item_requisicao_id,
            client_operation_id=key,
            version=projection.version,
            tipo_evento=event.tipo_evento,
            movimento_id=movement_id,
            projection=projection,
        )

    @classmethod
    async def validar_operacao_conciliada(
        cls, session: AsyncSession, tenant_id: UUID, operacao_id: UUID
    ) -> None:
        """Bloqueia fechamento normal enquanto houver posse/divergência pendente."""
        requisicoes = list(
            (
                await session.execute(
                    select(RequisicaoMaterial).where(
                        RequisicaoMaterial.tenant_id == tenant_id,
                        RequisicaoMaterial.operacao_agricola_id == operacao_id,
                    )
                )
            ).scalars().all()
        )
        for req in requisicoes:
            if req.compatibilidade_legado is not None:
                raise BusinessRuleError("A operação possui requisição legada não conciliável.")
            events = list(
                (
                    await session.execute(
                        select(RequisicaoItemEvento).where(
                            RequisicaoItemEvento.tenant_id == tenant_id,
                            RequisicaoItemEvento.requisicao_id == req.id,
                        )
                    )
                ).scalars().all()
            )
            if not events:
                raise BusinessRuleError("A operação possui requisição sem entrega/conciliação canônica.")
            by_item: dict[UUID, list[RequisicaoItemEvento]] = defaultdict(list)
            for event in events:
                by_item[event.item_requisicao_id].append(event)
            for item_events in by_item.values():
                delivered = sum(_number(e.quantidade) for e in item_events if e.tipo_evento == "ENTREGA")
                received = sum(_number(e.quantidade) for e in item_events if e.tipo_evento == "RECEBIMENTO")
                refused = sum(_number(e.quantidade) for e in item_events if e.tipo_evento == "RECUSA")
                destined = sum(_number(e.quantidade) for e in item_events if e.tipo_evento in DISPOSITION_TYPES)
                if delivered <= 0 or delivered - received - refused > 1e-9 or received - destined > 1e-9 or refused > 1e-9:
                    raise BusinessRuleError("A operação possui requisição não conciliada.")
