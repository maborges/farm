"""Subscriber econômico do evento operacional de consumo de materiais."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

from events.base import DomainEvent, EventSubscriber, EventSubscriberResult
from events.registry import register_event_subscriber

from .material_consumption_service import MaterialConsumptionCostService


@register_event_subscriber
class MaterialConsumptionCostSubscriber(EventSubscriber):
    """Projeta consumo canônico em CostAllocation uma única vez."""

    subscriber_name = "material-consumption-cost"
    event_types = ("operational.material_request.consumo",)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        """Processa o consumo mantendo retry seguro no Outbox."""
        started_at = perf_counter()
        if self.session is None or event.entity_id is None:
            raise ValueError("session e entity_id são obrigatórios para consumo econômico")
        allocation = await MaterialConsumptionCostService(
            self.session, event.tenant_id
        ).process(event.entity_id)
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name=self.subscriber_name,
            status="success",
            created=1,
            duration_ms=int((perf_counter() - started_at) * 1000),
            metadata={
                "cost_allocation_id": str(allocation.id),
                "requisicao_item_evento_id": str(event.entity_id),
                "processed_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
            },
        )
