from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.dispatcher import (
    AlertDispatcherResult,
    AlertDispatcherService,
    AlertDomainEvent,
)

from .base import DomainEvent, EventSubscriber, EventSubscriberResult
from .registry import register_event_subscriber


@register_event_subscriber
class AlertEngineEventSubscriber(EventSubscriber):
    """Subscriber that bridges domain events to the Alert Dispatcher."""

    subscriber_name = "alert-engine"
    event_types = (
        "campo.tarefa.invalidada",
        "campo.sync.falha",
        "pecuaria.vacinacao.registrada",
        "pecuaria.planejamento.sanitario.atualizado",
    )

    def __init__(
        self,
        session: AsyncSession | None = None,
        dispatcher: AlertDispatcherService | None = None,
    ) -> None:
        super().__init__(session=session)
        self.dispatcher = dispatcher

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        """Translate a domain event and invoke the Alert Dispatcher."""

        started_at = datetime.now(timezone.utc)  # noqa: UP017
        bound_logger = self._logger(event)
        bound_logger.info("alert_engine_event_subscriber_started")
        alert_event = self._to_alert_event(event)
        dispatcher_result = await self._dispatch(alert_event)
        result = self._to_result(event, dispatcher_result, started_at)
        bound_logger.bind(
            status=result.status,
            duration_ms=result.duration_ms,
            warnings=result.warnings,
            errors=result.errors,
            dispatch_id=result.metadata.get("dispatch_id"),
        ).info("alert_engine_event_subscriber_finished")
        return result

    async def _dispatch(self, event: AlertDomainEvent) -> AlertDispatcherResult:
        if self.dispatcher is not None:
            return await self.dispatcher.dispatch(event)
        if self.session is None:
            raise ValueError("session must be provided for AlertEngineEventSubscriber")
        return await AlertDispatcherService(self.session).dispatch(event)

    @staticmethod
    def _to_alert_event(event: DomainEvent) -> AlertDomainEvent:
        return AlertDomainEvent.model_validate(event.model_dump())

    @staticmethod
    def _logger(event: DomainEvent):
        return logger.bind(
            component="alert_engine_event_subscriber",
            event_id=str(event.event_id),
            event_type=event.event_type,
            tenant_id=str(event.tenant_id),
            unidade_produtiva_id=(
                str(event.unidade_produtiva_id) if event.unidade_produtiva_id else None
            ),
            correlation_id=str(event.correlation_id) if event.correlation_id else None,
            causation_id=str(event.causation_id) if event.causation_id else None,
            entity_type=event.entity_type,
            entity_id=str(event.entity_id) if event.entity_id else None,
        )

    @staticmethod
    def _to_result(
        event: DomainEvent,
        dispatcher_result: AlertDispatcherResult,
        started_at: datetime,
    ) -> EventSubscriberResult:
        finished_at = datetime.now(timezone.utc)  # noqa: UP017
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name="alert-engine",
            status="success" if dispatcher_result.errors == 0 else "failed",
            created=dispatcher_result.alerts_created,
            updated=dispatcher_result.alerts_updated,
            ignored=dispatcher_result.alerts_ignored,
            skipped=dispatcher_result.alerts_skipped,
            warnings=dispatcher_result.warnings,
            errors=dispatcher_result.errors,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            metadata={
                "dispatch_id": str(dispatcher_result.dispatch_id),
                "executions": [
                    execution.model_dump(mode="json")
                    for execution in dispatcher_result.executions
                ],
            },
        )


# Importing registers the official Recommendation subscriber in this existing
# default registry loading path; no second event registry is created.
from recommendations.event_subscriber import RecommendationEventSubscriber  # noqa: E402, F401
from agricola.romaneios.event_subscriber import RomaneioBalancaEventSubscriber  # noqa: E402, F401
from pecuaria.event_subscriber_balanca import PecuariaBalancaEventSubscriber  # noqa: E402, F401
from operacional.compras_event_subscriber import ComprasBalancaEventSubscriber  # noqa: E402, F401
from financeiro.comercializacao.event_subscriber import ComercializacaoBalancaEventSubscriber  # noqa: E402, F401
from agricola.custos.material_consumption_subscriber import MaterialConsumptionCostSubscriber  # noqa: E402, F401
