from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from time import perf_counter

from loguru import logger
from sqlalchemy import text

from core.exceptions import EntityNotFoundError, BusinessRuleError
from events.base import DomainEvent, EventSubscriber, EventSubscriberResult
from events.registry import register_event_subscriber

from agricola.romaneios.schemas import RomaneioColheitaUpdate
from agricola.romaneios.service import RomaneioService


@register_event_subscriber
class RomaneioBalancaEventSubscriber(EventSubscriber):
    """Reage a 'balanca.pesagem.concluida' quando origem_tipo=COLHEITA — atualiza
    peso_bruto_kg/tara_kg do romaneio com o valor oficial medido na balança.
    A Balança não conhece este módulo; o vínculo é só por origem_tipo/origem_id."""

    subscriber_name = "romaneios-balanca"
    event_types = ("balanca.pesagem.concluida",)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        started = perf_counter()

        if event.metadata.get("origem_tipo") != "COLHEITA":
            return self._result(event, "ignored", started, ignored=1, reason="origem_tipo != COLHEITA")

        origem_id = event.metadata.get("origem_id")
        if not origem_id:
            return self._result(event, "ignored", started, ignored=1, reason="sem origem_id")

        if self.session is None:
            raise ValueError("session must be provided for RomaneioBalancaEventSubscriber")

        await self._set_rls_context(event)
        svc = RomaneioService(self.session, event.tenant_id)

        try:
            peso_bruto = Decimal(event.metadata["peso_bruto_kg"])
            peso_tara = Decimal(event.metadata["peso_tara_kg"])
        except (KeyError, InvalidOperation) as exc:
            return self._result(event, "failed", started, errors=1, reason=f"payload inválido: {exc}")

        try:
            # Sem commit aqui de propósito — o relay (outbox_relay.run_once) comita
            # tudo junto no final (atualização do romaneio + status do outbox na
            # mesma transação). Commitar aqui no meio corrompe a transação do relay.
            await svc.atualizar(
                uuid.UUID(origem_id),
                RomaneioColheitaUpdate(peso_bruto_kg=float(peso_bruto), tara_kg=float(peso_tara)),
            )
        except EntityNotFoundError:
            return self._result(event, "ignored", started, ignored=1, reason="romaneio não encontrado")
        except BusinessRuleError as exc:
            return self._result(event, "failed", started, errors=1, reason=str(exc))

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
            component="romaneio_balanca_event_subscriber",
            event_id=str(event.event_id),
            event_type=event.event_type,
            tenant_id=str(event.tenant_id),
            entity_id=str(event.entity_id) if event.entity_id else None,
            outcome=status,
            duration_ms=duration_ms,
        ).info("romaneio_balanca_event_subscriber_finished")
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
