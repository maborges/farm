from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from time import perf_counter

from loguru import logger
from sqlalchemy import select, text

from events.base import DomainEvent, EventSubscriber, EventSubscriberResult
from events.registry import register_event_subscriber

from pecuaria.animal.models import Animal, EventoAnimal
from integracoes.balanca.events import BALANCA_COMPLETED_EVENT, completed_weighing_metadata


@register_event_subscriber
class PecuariaBalancaEventSubscriber(EventSubscriber):
    """Reage a 'balanca.pesagem.concluida' quando origem_tipo=PECUARIA — registra
    um EventoAnimal(tipo=PESAGEM) e atualiza Animal.peso_atual_kg. Escreve os
    mesmos campos que pecuaria.services.pesagem_service.PesagemService.
    registrar_pesagem() gravaria, mas sem chamar aquele método diretamente: ele
    comita a própria transação, o que corrompe a transação do outbox relay
    quando chamado no meio do processamento de um evento."""

    subscriber_name = "pecuaria-balanca"
    event_types = ("balanca.pesagem.concluida", BALANCA_COMPLETED_EVENT)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        started = perf_counter()

        metadata = completed_weighing_metadata(event)
        if metadata.get("origem_tipo") != "PECUARIA":
            return self._result(event, "ignored", started, ignored=1, reason="origem_tipo != PECUARIA")

        origem_id = metadata.get("origem_id")
        if not origem_id:
            return self._result(event, "ignored", started, ignored=1, reason="sem origem_id")

        if self.session is None:
            raise ValueError("session must be provided for PecuariaBalancaEventSubscriber")

        await self._set_rls_context(event)

        try:
            peso_liquido = Decimal(metadata["peso_liquido_kg"])
        except (KeyError, InvalidOperation) as exc:
            return self._result(event, "failed", started, errors=1, reason=f"payload inválido: {exc}")

        animal_id = uuid.UUID(origem_id)
        animal = (
            await self.session.execute(
                select(Animal).where(Animal.id == animal_id, Animal.tenant_id == event.tenant_id)
            )
        ).scalars().first()
        if not animal:
            return self._result(event, "ignored", started, ignored=1, reason="animal não encontrado")

        hoje = date.today()
        evento = EventoAnimal(
            tenant_id=event.tenant_id,
            animal_id=animal_id,
            tipo="PESAGEM",
            data_evento=hoje,
            peso_kg=float(peso_liquido),
            observacoes=f"Pesagem oficial via balança (ordem {event.entity_id})",
        )
        self.session.add(evento)

        if animal.data_ultima_pesagem is None or hoje >= animal.data_ultima_pesagem:
            animal.peso_atual_kg = float(peso_liquido)
            animal.data_ultima_pesagem = hoje

        await self.session.flush()
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
            component="pecuaria_balanca_event_subscriber",
            event_id=str(event.event_id),
            event_type=event.event_type,
            tenant_id=str(event.tenant_id),
            entity_id=str(event.entity_id) if event.entity_id else None,
            outcome=status,
            duration_ms=duration_ms,
        ).info("pecuaria_balanca_event_subscriber_finished")
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
