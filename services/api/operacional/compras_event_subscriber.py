from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from time import perf_counter

from loguru import logger
from sqlalchemy import text

from core.exceptions import EntityNotFoundError
from events.base import DomainEvent, EventSubscriber, EventSubscriberResult
from events.registry import register_event_subscriber

from operacional.services.compras_service import ComprasService
from integracoes.balanca.events import BALANCA_COMPLETED_EVENT, completed_weighing_metadata


@register_event_subscriber
class ComprasBalancaEventSubscriber(EventSubscriber):
    """Reage a 'balanca.pesagem.concluida' quando origem_tipo=COMPRA — grava o
    peso oficial medido na balança em PedidoCompra. Não confundir com
    `quantidade_recebida` (unidade do item) — peso é informativo/confirmatório,
    o recebimento em si (`receber_pedido`) continua manual."""

    subscriber_name = "compras-balanca"
    event_types = ("balanca.pesagem.concluida", BALANCA_COMPLETED_EVENT)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        started = perf_counter()

        metadata = completed_weighing_metadata(event)
        if metadata.get("origem_tipo") != "COMPRA":
            return self._result(event, "ignored", started, ignored=1, reason="origem_tipo != COMPRA")

        origem_id = metadata.get("origem_id")
        if not origem_id:
            return self._result(event, "ignored", started, ignored=1, reason="sem origem_id")

        if self.session is None:
            raise ValueError("session must be provided for ComprasBalancaEventSubscriber")

        await self._set_rls_context(event)

        try:
            peso_bruto = Decimal(metadata["peso_bruto_kg"])
            peso_tara = Decimal(metadata["peso_tara_kg"])
        except (KeyError, InvalidOperation) as exc:
            return self._result(event, "failed", started, errors=1, reason=f"payload inválido: {exc}")

        svc = ComprasService(self.session, event.tenant_id)
        try:
            await svc.atualizar_peso_balanca(uuid.UUID(origem_id), float(peso_bruto), float(peso_tara))
        except EntityNotFoundError:
            return self._result(event, "ignored", started, ignored=1, reason="pedido não encontrado")

        return self._result(event, "processed", started, updated=1)

    async def _set_rls_context(self, event: DomainEvent) -> None:
        if self.session is None:
            return
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(event.tenant_id)},
        )

    def _result(
        self,
        event: DomainEvent,
        status: str,
        started: float,
        *,
        updated: int = 0,
        ignored: int = 0,
        errors: int = 0,
        reason: str | None = None,
    ) -> EventSubscriberResult:
        duration_ms = int((perf_counter() - started) * 1000)
        metadata = {"outcome": status}
        if reason:
            metadata["reason"] = reason
        logger.bind(
            component="compras_balanca_event_subscriber",
            event_id=str(event.event_id),
            event_type=event.event_type,
            tenant_id=str(event.tenant_id),
            entity_id=str(event.entity_id) if event.entity_id else None,
            outcome=status,
            duration_ms=duration_ms,
        ).info("compras_balanca_event_subscriber_finished")
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name=self.subscriber_name,
            status=status,
            updated=updated,
            ignored=ignored,
            errors=errors,
            duration_ms=duration_ms,
            metadata=metadata,
        )
