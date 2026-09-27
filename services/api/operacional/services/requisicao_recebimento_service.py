"""Recebimento canônico de materiais no Campo (01E).

Este serviço registra somente fatos de custódia no diário da requisição.  A
entrega já realizou a única saída física; portanto nenhum método deste módulo
consulta ou altera saldo, lote ou reserva como efeito do recebimento.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.cadastros.models import ProdutoCatalogo
from agricola.operacoes.models import OperacaoExecucao
from campo.models import DispositivoCampo
from events import DomainEvent, DomainEventOutboxService
from operacional.domain.requisicao_material import TipoRequisicaoItemEvento
from operacional.models.estoque import (
    ItemRequisicao,
    RequisicaoItemEvento,
    RequisicaoMaterial,
    RequisicaoResponsabilidadeHistorico,
)
from operacional.schemas.estoque import (
    EntregaCampoProjection,
    ItemRequisicaoCampoProjection,
    RecebimentoCampoAck,
    RecebimentoRequisicaoRequest,
    OperacaoExecucaoCampoProjection,
    RequisicaoCampoProjection,
)
from operacional.services.identidade_operacional_service import IdentidadeOperacionalService


RECEIPT_RESULTS = {
    "RECEBIDO_INTEGRAL",
    "RECEBIDO_PARCIAL",
    "RECUSADO",
    "DIVERGENTE",
}
RECEIPT_EVENT_TYPES = {
    TipoRequisicaoItemEvento.RECEBIMENTO.value,
    TipoRequisicaoItemEvento.RECUSA.value,
}


def _number(value: Decimal | float | int | None) -> float:
    return float(value or 0)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RequisicaoRecebimentoService:
    """Comandos/projeções do recebimento, com autorização no backend."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def listar_para_campo(
        self,
        *,
        device: DispositivoCampo,
        usuario_id: UUID,
        operacao_agricola_id: UUID | None = None,
    ) -> list[RequisicaoCampoProjection]:
        """Retorna somente requisições entregues ao responsável/delegado."""
        try:
            identidade = await IdentidadeOperacionalService.resolver_pessoa_usuario(
                self.session, self.tenant_id, usuario_id
            )
        except (EntityNotFoundError, BusinessRuleError):
            return []

        fazenda_ids = [UUID(str(value)) for value in (device.fazenda_ids or [])]
        delegado = exists(
            select(1).where(
                RequisicaoResponsabilidadeHistorico.tenant_id == self.tenant_id,
                RequisicaoResponsabilidadeHistorico.requisicao_id == RequisicaoMaterial.id,
                RequisicaoResponsabilidadeHistorico.usuario_id == usuario_id,
                RequisicaoResponsabilidadeHistorico.pessoa_usuario_id == identidade.id,
                RequisicaoResponsabilidadeHistorico.papel == "DELEGADO",
                RequisicaoResponsabilidadeHistorico.vigencia_inicio <= func.current_timestamp(),
                or_(
                    RequisicaoResponsabilidadeHistorico.vigencia_fim.is_(None),
                    RequisicaoResponsabilidadeHistorico.vigencia_fim > func.current_timestamp(),
                ),
            )
        )
        delivery_exists = exists(
            select(1).where(
                RequisicaoItemEvento.tenant_id == self.tenant_id,
                RequisicaoItemEvento.requisicao_id == RequisicaoMaterial.id,
                RequisicaoItemEvento.tipo_evento == TipoRequisicaoItemEvento.ENTREGA.value,
            )
        )
        conditions = [
            RequisicaoMaterial.tenant_id == self.tenant_id,
            RequisicaoMaterial.unidade_produtiva_id.in_(fazenda_ids),
            delivery_exists,
            or_(
                RequisicaoMaterial.responsavel_pessoa_id == identidade.pessoa_id,
                delegado,
            ),
        ]
        if operacao_agricola_id is not None:
            conditions.append(RequisicaoMaterial.operacao_agricola_id == operacao_agricola_id)

        requisicoes = list(
            (
                await self.session.execute(
                    select(RequisicaoMaterial).where(and_(*conditions)).order_by(
                        RequisicaoMaterial.data_solicitacao.desc()
                    )
                )
            )
            .scalars()
            .all()
        )
        result: list[RequisicaoCampoProjection] = []
        for requisicao in requisicoes:
            projection = await self._project_request(requisicao, responsavel_autorizado=True)
            if any(item.quantidade_entregue > 0 for item in projection.itens):
                result.append(projection)
        return result

    async def receber(
        self,
        requisicao_id: UUID,
        data: RecebimentoRequisicaoRequest,
        *,
        usuario_id: UUID,
        dispositivo_id: UUID,
    ) -> RecebimentoCampoAck:
        requisicao, item = await self._lock_request_item(requisicao_id, data.item_id)
        identidade = await IdentidadeOperacionalService.validar_recebedor(
            self.session, self.tenant_id, requisicao_id, usuario_id
        )

        existing = await self._find_idempotent(data.client_operation_id)
        if existing is not None:
            self._validate_retry(existing, data)
            if existing.requisicao_id != requisicao.id or existing.usuario_id != usuario_id:
                raise BusinessRuleError(
                    "client_operation_id pertence a outro contexto operacional."
                )
            projection = await self._project_request(requisicao, responsavel_autorizado=True)
            return RecebimentoCampoAck(
                evento_id=existing.id,
                requisicao_id=requisicao.id,
                item_id=existing.item_requisicao_id,
                client_operation_id=data.client_operation_id,
                version=requisicao.version,
                resultado=existing.resultado_conferencia or data.resultado,
                projection=projection,
            )

        if requisicao.compatibilidade_legado is not None:
            raise BusinessRuleError("Requisição legada não pode receber pelo fluxo canônico.")
        if requisicao.status in {"CANCELADA", "RECUSADA"}:
            raise BusinessRuleError("Requisição cancelada ou recusada não pode ser recebida.")
        if data.base_version != requisicao.version:
            raise BusinessRuleError("Versão da requisição obsoleta; sincronize antes de conferir.")
        if data.dispositivo_id != dispositivo_id:
            raise BusinessRuleError("O dispositivo do comando não corresponde ao token autenticado.")

        entrega = (
            await self.session.execute(
                select(RequisicaoItemEvento)
                .where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.id == data.entrega_evento_id,
                    RequisicaoItemEvento.requisicao_id == requisicao_id,
                    RequisicaoItemEvento.item_requisicao_id == item.id,
                    RequisicaoItemEvento.tipo_evento == TipoRequisicaoItemEvento.ENTREGA.value,
                    RequisicaoItemEvento.provenance == "CANONICAL",
                )
                .with_for_update()
            )
        ).scalars().first()
        if entrega is None:
            raise EntityNotFoundError("Entrega canônica não encontrada para este item.")

        recebida, recusada = await self._accepted_and_refused(entrega.id)
        entregue = _number(entrega.quantidade)
        pendente = max(0.0, entregue - recebida - recusada)
        quantidade = _number(data.quantidade_recebida)
        if pendente <= 1e-9:
            raise BusinessRuleError("Esta entrega já foi totalmente conferida.")

        evento_tipo = TipoRequisicaoItemEvento.RECEBIMENTO.value
        evento_quantidade = quantidade
        if data.resultado == "RECUSADO":
            if quantidade != 0:
                raise BusinessRuleError("Recusa deve informar quantidade recebida igual a zero.")
            if not data.motivo or not data.motivo.strip():
                raise BusinessRuleError("A recusa exige motivo auditável.")
            evento_tipo = TipoRequisicaoItemEvento.RECUSA.value
            evento_quantidade = pendente
        else:
            if quantidade <= 0 or quantidade > pendente + 1e-9:
                raise BusinessRuleError("Quantidade recebida excede a entrega pendente.")
            total_apos = recebida + quantidade
            if data.resultado == "RECEBIDO_INTEGRAL" and total_apos < entregue - 1e-9:
                raise BusinessRuleError("Recebimento integral exige fechar a quantidade entregue.")
            if data.resultado in {"RECEBIDO_PARCIAL", "DIVERGENTE"}:
                if total_apos >= entregue - 1e-9:
                    raise BusinessRuleError("Resultado parcial/divergente exige quantidade pendente.")
                if not data.motivo or not data.motivo.strip():
                    raise BusinessRuleError("Recebimento parcial/divergente exige motivo.")

        requisicao.version += 1
        evento = RequisicaoItemEvento(
            tenant_id=self.tenant_id,
            requisicao_id=requisicao.id,
            item_requisicao_id=item.id,
            tipo_evento=evento_tipo,
            quantidade=evento_quantidade,
            unidade=entrega.unidade,
            produto_id=item.produto_id,
            lote_id=entrega.lote_id,
            deposito_id=entrega.deposito_id,
            operacao_agricola_id=requisicao.operacao_agricola_id,
            usuario_id=usuario_id,
            pessoa_operacional_id=identidade.pessoa_id,
            dispositivo_id=dispositivo_id,
            ocorrido_em_dispositivo=data.ocorrido_em_dispositivo,
            motivo=data.motivo,
            versao_requisicao=requisicao.version,
            correlation_id=uuid4(),
            causation_id=entrega.id,
            evento_entrega_id=entrega.id,
            resultado_conferencia=data.resultado,
            client_operation_id=data.client_operation_id,
            provenance="CANONICAL",
        )
        self.session.add(evento)
        try:
            await self.session.flush()
        except IntegrityError:
            # Duas sessões podem passar pela leitura inicial ao mesmo tempo.
            # A UNIQUE tenant + client_operation_id é a arbitragem final; se
            # outra sessão confirmou primeiro, convergimos ao fato canônico
            # em vez de expor IntegrityError ao Campo.
            await self.session.rollback()
            existing = await self._find_idempotent(data.client_operation_id)
            if existing is None:
                raise
            self._validate_retry(existing, data)
            if existing.requisicao_id != requisicao.id or existing.usuario_id != usuario_id:
                raise BusinessRuleError(
                    "client_operation_id pertence a outro contexto operacional."
                )
            requisicao = await self._request_for_event(existing)
            projection = await self._project_request(requisicao, responsavel_autorizado=True)
            return RecebimentoCampoAck(
                evento_id=existing.id,
                requisicao_id=requisicao.id,
                item_id=existing.item_requisicao_id,
                client_operation_id=data.client_operation_id,
                version=requisicao.version,
                resultado=existing.resultado_conferencia or data.resultado,
                projection=projection,
            )
        await DomainEventOutboxService(self.session, self.tenant_id).enqueue(
            DomainEvent(
                tenant_id=self.tenant_id,
                unidade_produtiva_id=requisicao.unidade_produtiva_id,
                domain="operacional",
                event_type=(
                    "operational.material_request.refused"
                    if evento_tipo == TipoRequisicaoItemEvento.RECUSA.value
                    else "operational.material_request.received"
                ),
                source_type="RequisicaoItemEvento",
                entity_type="RequisicaoItemEvento",
                entity_id=evento.id,
                correlation_id=evento.correlation_id,
                metadata={
                    "requisicao_id": str(requisicao.id),
                    "item_requisicao_id": str(item.id),
                    "evento_entrega_id": str(entrega.id),
                    "quantidade_recebida": quantidade,
                    "resultado": data.resultado,
                    "client_operation_id": data.client_operation_id,
                },
            ),
            commit=False,
        )
        projection = await self._project_request(requisicao, responsavel_autorizado=True)
        return RecebimentoCampoAck(
            evento_id=evento.id,
            requisicao_id=requisicao.id,
            item_id=item.id,
            client_operation_id=data.client_operation_id,
            version=requisicao.version,
            resultado=data.resultado,
            projection=projection,
        )

    async def _lock_request_item(
        self, requisicao_id: UUID, item_id: UUID
    ) -> tuple[RequisicaoMaterial, ItemRequisicao]:
        row = (
            await self.session.execute(
                select(RequisicaoMaterial, ItemRequisicao)
                .join(ItemRequisicao, ItemRequisicao.requisicao_id == RequisicaoMaterial.id)
                .where(
                    RequisicaoMaterial.tenant_id == self.tenant_id,
                    RequisicaoMaterial.id == requisicao_id,
                    ItemRequisicao.tenant_id == self.tenant_id,
                    ItemRequisicao.id == item_id,
                )
                .with_for_update()
            )
        ).first()
        if row is None:
            raise EntityNotFoundError("Requisição ou item não pertence ao tenant atual.")
        return row

    async def _request_for_event(self, event: RequisicaoItemEvento) -> RequisicaoMaterial:
        requisicao = (
            await self.session.execute(
                select(RequisicaoMaterial).where(
                    RequisicaoMaterial.tenant_id == self.tenant_id,
                    RequisicaoMaterial.id == event.requisicao_id,
                )
            )
        ).scalars().first()
        if requisicao is None:
            raise EntityNotFoundError("Requisição do evento não encontrada.")
        return requisicao

    async def _find_idempotent(self, client_operation_id: str) -> RequisicaoItemEvento | None:
        return (
            await self.session.execute(
                select(RequisicaoItemEvento).where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.client_operation_id == client_operation_id,
                    RequisicaoItemEvento.tipo_evento.in_(RECEIPT_EVENT_TYPES),
                )
            )
        ).scalars().first()

    @staticmethod
    def _validate_retry(event: RequisicaoItemEvento, data: RecebimentoRequisicaoRequest) -> None:
        expected_type = (
            TipoRequisicaoItemEvento.RECUSA.value
            if data.resultado == "RECUSADO"
            else TipoRequisicaoItemEvento.RECEBIMENTO.value
        )
        quantity_matches = (
            data.resultado == "RECUSADO"
            or abs(_number(event.quantidade) - _number(data.quantidade_recebida)) <= 1e-9
        )
        if (
            event.item_requisicao_id != data.item_id
            or event.evento_entrega_id != data.entrega_evento_id
            or event.tipo_evento != expected_type
            or not quantity_matches
            or event.resultado_conferencia != data.resultado
        ):
            raise BusinessRuleError("client_operation_id já identifica outro recebimento.")

    async def _accepted_and_refused(self, entrega_evento_id: UUID) -> tuple[float, float]:
        rows = (
            await self.session.execute(
                select(RequisicaoItemEvento.tipo_evento, func.coalesce(func.sum(RequisicaoItemEvento.quantidade), 0))
                .where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.evento_entrega_id == entrega_evento_id,
                    RequisicaoItemEvento.tipo_evento.in_(RECEIPT_EVENT_TYPES),
                )
                .group_by(RequisicaoItemEvento.tipo_evento)
            )
        ).all()
        values = {row[0]: _number(row[1]) for row in rows}
        return (
            values.get(TipoRequisicaoItemEvento.RECEBIMENTO.value, 0.0),
            values.get(TipoRequisicaoItemEvento.RECUSA.value, 0.0),
        )

    async def _project_request(
        self, requisicao: RequisicaoMaterial, *, responsavel_autorizado: bool
    ) -> RequisicaoCampoProjection:
        items = list(
            (
                await self.session.execute(
                    select(ItemRequisicao).where(
                        ItemRequisicao.tenant_id == self.tenant_id,
                        ItemRequisicao.requisicao_id == requisicao.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        product_ids = [item.produto_id for item in items]
        products = {
            row.id: row
            for row in (
                await self.session.execute(select(ProdutoCatalogo).where(ProdutoCatalogo.id.in_(product_ids)))
            )
            .scalars()
            .all()
        }
        events = list(
            (
                await self.session.execute(
                    select(RequisicaoItemEvento)
                    .where(
                        RequisicaoItemEvento.tenant_id == self.tenant_id,
                        RequisicaoItemEvento.requisicao_id == requisicao.id,
                    )
                    .order_by(RequisicaoItemEvento.ocorrido_em, RequisicaoItemEvento.created_at)
                )
            )
            .scalars()
            .all()
        )
        by_item: dict[UUID, list[RequisicaoItemEvento]] = defaultdict(list)
        for event in events:
            by_item[event.item_requisicao_id].append(event)

        item_projections: list[ItemRequisicaoCampoProjection] = []
        for item in items:
            item_events = by_item[item.id]
            deliveries = [
                event
                for event in item_events
                if event.tipo_evento == TipoRequisicaoItemEvento.ENTREGA.value
            ]
            received_events = [
                event
                for event in item_events
                if event.tipo_evento == TipoRequisicaoItemEvento.RECEBIMENTO.value
            ]
            refused_events = [
                event for event in item_events if event.tipo_evento == TipoRequisicaoItemEvento.RECUSA.value
            ]
            received_total = sum(_number(event.quantidade) for event in received_events)
            refused_total = sum(_number(event.quantidade) for event in refused_events)
            disposition_totals = {
                event_type: sum(
                    _number(event.quantidade)
                    for event in item_events
                    if event.tipo_evento == event_type
                )
                for event_type in (
                    TipoRequisicaoItemEvento.CONSUMO.value,
                    TipoRequisicaoItemEvento.DEVOLUCAO.value,
                    TipoRequisicaoItemEvento.PERDA.value,
                    TipoRequisicaoItemEvento.DANO.value,
                    TipoRequisicaoItemEvento.EXTRAVIO.value,
                )
            }
            disposition_total = sum(disposition_totals.values())
            delivery_projections: list[EntregaCampoProjection] = []
            for delivery in deliveries:
                received, refused = await self._accepted_and_refused(delivery.id)
                delivery_dispositions = await self._disposition_totals(delivery.id)
                delivery_possession = max(0.0, received - sum(delivery_dispositions.values()))
                delivery_pending = max(0.0, _number(delivery.quantidade) - received - refused)
                delivery_status = self._conciliation_status(
                    delivery_pending, refused, delivery_possession
                )
                delivery_projections.append(
                    EntregaCampoProjection(
                        id=delivery.id,
                        quantidade_entregue=_number(delivery.quantidade),
                        quantidade_recebida=received,
                        quantidade_recusada=refused,
                        quantidade_pendente_conferencia=delivery_pending,
                        quantidade_consumida=delivery_dispositions.get(TipoRequisicaoItemEvento.CONSUMO.value, 0.0),
                        quantidade_devolvida=delivery_dispositions.get(TipoRequisicaoItemEvento.DEVOLUCAO.value, 0.0),
                        quantidade_perdida=delivery_dispositions.get(TipoRequisicaoItemEvento.PERDA.value, 0.0),
                        quantidade_danificada=delivery_dispositions.get(TipoRequisicaoItemEvento.DANO.value, 0.0),
                        quantidade_extraviada=delivery_dispositions.get(TipoRequisicaoItemEvento.EXTRAVIO.value, 0.0),
                        quantidade_em_posse=delivery_possession,
                        status_conciliacao=delivery_status,
                        lote_id=delivery.lote_id,
                        deposito_id=delivery.deposito_id,
                        unidade=delivery.unidade,
                        entregue_em=delivery.ocorrido_em,
                    )
                )
            delivered_total = sum(entry.quantidade_entregue for entry in delivery_projections)
            pending_total = max(0.0, delivered_total - received_total - refused_total)
            if delivered_total <= 1e-9:
                status = "SEM_ENTREGA"
            elif pending_total > 1e-9:
                status = "DIVERGENTE" if received_total > 0 else "PENDENTE_CONFERENCIA"
            elif refused_total > 0 and received_total <= 1e-9:
                status = "RECUSADO"
            elif refused_total > 0:
                status = "DIVERGENTE"
            else:
                status = "RECEBIDO_INTEGRAL"
            status_conciliacao = self._conciliation_status(
                pending_total, refused_total, max(0.0, received_total - disposition_total)
            )
            item_projections.append(
                ItemRequisicaoCampoProjection(
                    id=item.id,
                    produto_id=item.produto_id,
                    produto_nome=getattr(products.get(item.produto_id), "nome", None),
                    natureza_item=item.natureza_item,
                    unidade=(delivery_projections[0].unidade if delivery_projections else getattr(products.get(item.produto_id), "unidade_medida", "")),
                    quantidade_aprovada=_number(item.quantidade_aprovada),
                    quantidade_entregue=delivered_total,
                    quantidade_recebida=received_total,
                    quantidade_recusada=refused_total,
                    quantidade_pendente_conferencia=pending_total,
                    quantidade_em_posse=max(0.0, received_total - disposition_total),
                    quantidade_consumida=disposition_totals[TipoRequisicaoItemEvento.CONSUMO.value],
                    quantidade_devolvida=disposition_totals[TipoRequisicaoItemEvento.DEVOLUCAO.value],
                    quantidade_perdida=disposition_totals[TipoRequisicaoItemEvento.PERDA.value],
                    quantidade_danificada=disposition_totals[TipoRequisicaoItemEvento.DANO.value],
                    quantidade_extraviada=disposition_totals[TipoRequisicaoItemEvento.EXTRAVIO.value],
                    status_conferencia=status,
                    status_conciliacao=status_conciliacao,
                    entregas=delivery_projections,
                )
            )

        statuses = {item.status_conferencia for item in item_projections if item.quantidade_entregue > 0}
        if statuses and statuses <= {"RECEBIDO_INTEGRAL"}:
            status_efetivo = "RECEBIDA"
        elif "RECUSADO" in statuses or "DIVERGENTE" in statuses:
            status_efetivo = "DIVERGENTE"
        else:
            status_efetivo = "PENDENTE_CONFERENCIA"
        reconciliation_statuses = {
            item.status_conciliacao
            for item in item_projections
            if item.quantidade_entregue > 0
        }
        if reconciliation_statuses and reconciliation_statuses <= {"CONCILIADO"}:
            status_conciliacao = "CONCILIADA"
        elif "PENDENTE_DIVERGENCIA" in reconciliation_statuses or "PENDENTE_RECUSA" in reconciliation_statuses:
            status_conciliacao = "PENDENTE_DIVERGENCIA"
        elif "EM_POSSE" in reconciliation_statuses:
            status_conciliacao = "EM_POSSE"
        else:
            status_conciliacao = "PENDENTE_CONCILIACAO"
        execucoes: list[OperacaoExecucaoCampoProjection] = []
        if requisicao.operacao_agricola_id is not None:
            execucoes = [
                OperacaoExecucaoCampoProjection(
                    id=execution.id,
                    status=execution.status,
                    data_execucao=execution.data_execucao,
                )
                for execution in (
                    await self.session.execute(
                        select(OperacaoExecucao)
                        .where(
                            OperacaoExecucao.tenant_id == self.tenant_id,
                            OperacaoExecucao.operacao_id == requisicao.operacao_agricola_id,
                        )
                        .order_by(OperacaoExecucao.data_execucao, OperacaoExecucao.created_at)
                    )
                ).scalars().all()
            ]
        return RequisicaoCampoProjection(
            id=requisicao.id,
            numero=requisicao.numero,
            tenant_id=requisicao.tenant_id,
            unidade_produtiva_id=requisicao.unidade_produtiva_id,
            safra_id=requisicao.safra_id,
            safra_tarefa_id=requisicao.safra_tarefa_id,
            operacao_agricola_id=requisicao.operacao_agricola_id,
            responsavel_pessoa_id=requisicao.responsavel_pessoa_id,
            responsavel_autorizado=responsavel_autorizado,
            version=requisicao.version,
            status=requisicao.status,
            status_efetivo=status_efetivo,
            status_conciliacao=status_conciliacao,
            data_solicitacao=requisicao.data_solicitacao,
            execucoes=execucoes,
            itens=item_projections,
        )

    @staticmethod
    def _conciliation_status(pending: float, refused: float, possession: float) -> str:
        if pending > 1e-9:
            return "PENDENTE_DIVERGENCIA"
        if refused > 1e-9:
            return "PENDENTE_RECUSA"
        if possession > 1e-9:
            return "EM_POSSE"
        return "CONCILIADO"

    async def _disposition_totals(self, delivery_event_id: UUID) -> dict[str, float]:
        rows = (
            await self.session.execute(
                select(RequisicaoItemEvento.tipo_evento, func.sum(RequisicaoItemEvento.quantidade))
                .where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.evento_entrega_id == delivery_event_id,
                    RequisicaoItemEvento.tipo_evento.in_(
                        {
                            TipoRequisicaoItemEvento.CONSUMO.value,
                            TipoRequisicaoItemEvento.DEVOLUCAO.value,
                            TipoRequisicaoItemEvento.PERDA.value,
                            TipoRequisicaoItemEvento.DANO.value,
                            TipoRequisicaoItemEvento.EXTRAVIO.value,
                        }
                    ),
                )
                .group_by(RequisicaoItemEvento.tipo_evento)
            )
        ).all()
        return {row[0]: _number(row[1]) for row in rows}
