from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from events.base import DomainEvent, EventSubscriber, EventSubscriberResult
from events.registry import register_event_subscriber

from .engine import RecommendationEngine
from .event_mapper import RecommendationEventContractError, RecommendationEventMapper
from .registry import RecommendationProviderRegistry


@register_event_subscriber
class RecommendationEventSubscriber(EventSubscriber):
    """Bridge supported Outbox events to the global RecommendationEngine."""

    subscriber_name = "recommendations"
    event_types = ("campo.sync.falha",)

    def __init__(
        self,
        session: AsyncSession | None = None,
        mapper: RecommendationEventMapper | None = None,
        registry: RecommendationProviderRegistry | None = None,
        engine_factory: Callable[..., RecommendationEngine] = RecommendationEngine,
    ) -> None:
        super().__init__(session=session)
        self.mapper = mapper or RecommendationEventMapper()
        self.registry = registry
        self.engine_factory = engine_factory

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        """Map, evaluate, and persist one event without owning recommendation rules."""

        started = perf_counter()
        try:
            mapping = self.mapper.map(event)
        except RecommendationEventContractError as exc:
            return self._result(event, "rejected", started, ignored=1, reason=str(exc))
        if mapping is None:
            return self._result(event, "ignored", started, ignored=1)
        try:
            engine_result = await self._evaluate(event, mapping)
        except Exception as exc:  # pragma: no cover - relay retry contract
            return self._result(event, "failed", started, errors=1, reason=exc.__class__.__name__)
        return self._result(
            event,
            "processed" if engine_result.errors == 0 else "failed",
            started,
            created=engine_result.recommendations_created,
            updated=engine_result.recommendations_updated,
            errors=engine_result.errors,
            providers=[execution.provider_name for execution in engine_result.executions],
        )

    async def _evaluate(self, event: DomainEvent, mapping):
        if self.session is None:
            raise ValueError("session must be provided for RecommendationEventSubscriber")
        await self._set_rls_context(event)
        engine = self.engine_factory(self.session, event.tenant_id, registry=self.registry)
        return await engine.generate(
            mapping.context,
            [mapping.signal],
            provider_names=list(mapping.provider_names),
        )

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
        created: int = 0,
        updated: int = 0,
        ignored: int = 0,
        errors: int = 0,
        reason: str | None = None,
        providers: list[str] | None = None,
    ) -> EventSubscriberResult:
        duration_ms = int((perf_counter() - started) * 1000)
        metadata = {"outcome": status, "providers_evaluated": providers or []}
        if reason:
            metadata["reason"] = reason
        logger.bind(
            component="recommendation_event_subscriber",
            event_id=str(event.event_id),
            event_type=event.event_type,
            tenant_id=str(event.tenant_id),
            scope_type=event.entity_type,
            scope_id=str(event.entity_id) if event.entity_id else None,
            providers_evaluated=providers or [],
            recommendations_generated=created,
            recommendations_updated=updated,
            failures=errors,
            duration_ms=duration_ms,
            retry_attempt=event.metadata.get("retry_attempt"),
            outcome=status,
        ).info("recommendation_event_subscriber_finished")
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name=self.subscriber_name,
            status=status,
            created=created,
            updated=updated,
            ignored=ignored,
            errors=errors,
            duration_ms=duration_ms,
            metadata=metadata,
        )
