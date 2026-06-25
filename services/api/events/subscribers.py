from __future__ import annotations

from datetime import datetime, timezone

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
        alert_event = self._to_alert_event(event)
        dispatcher_result = await self._dispatch(alert_event)
        return self._to_result(event, dispatcher_result, started_at)

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
