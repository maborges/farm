from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

from events.base import DomainEvent

from .enums import RecommendationDomain, RecommendationSourceType
from .schemas import OperationalContext, RecommendationSignal


class RecommendationEventContractError(ValueError):
    """Raised when an eligible domain event lacks recommendation context."""


@dataclass(frozen=True, slots=True)
class RecommendationEventMapping:
    """Canonical event input for one focused recommendation evaluation."""

    signal: RecommendationSignal
    context: OperationalContext
    provider_names: tuple[str, ...]


class RecommendationEventMapper:
    """Translate eligible domain events without evaluating recommendation rules."""

    _EVENT_PROVIDERS: Final[dict[str, tuple[RecommendationDomain, tuple[str, ...]]]] = {
        "campo.sync.falha": (RecommendationDomain.FIELD, ("campo",)),
    }

    def map(self, event: DomainEvent) -> RecommendationEventMapping | None:
        """Return a focused engine input, or None for an unsupported event."""

        configuration = self._EVENT_PROVIDERS.get(event.event_type.lower())
        if configuration is None:
            return None
        self._validate_scope(event)
        domain, provider_names = configuration
        signal = self._build_signal(event, domain)
        return RecommendationEventMapping(
            signal=signal,
            context=self._build_context(event, domain),
            provider_names=provider_names,
        )

    @staticmethod
    def _validate_scope(event: DomainEvent) -> None:
        if not isinstance(event.tenant_id, UUID):
            raise RecommendationEventContractError("event tenant_id is required")
        if event.entity_id is None or not event.entity_type:
            raise RecommendationEventContractError("event entity scope is required")

    @staticmethod
    def _build_signal(event: DomainEvent, domain: RecommendationDomain) -> RecommendationSignal:
        return RecommendationSignal(
            signal_id=event.event_id,
            tenant_id=event.tenant_id,
            unidade_produtiva_id=event.unidade_produtiva_id,
            domain=domain,
            source_type=RecommendationSourceType.EVENT,
            key=event.event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            occurred_at=event.occurred_at,
            payload={"source_event_id": str(event.event_id), **dict(event.metadata)},
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            metadata={"event_type": event.event_type},
        )

    @staticmethod
    def _build_context(event: DomainEvent, domain: RecommendationDomain) -> OperationalContext:
        return OperationalContext(
            tenant_id=event.tenant_id,
            unidade_produtiva_id=event.unidade_produtiva_id,
            domain=domain,
            scope_type=event.entity_type or "EVENT",
            scope_id=str(event.entity_id),
            source_signal_ids=[event.event_id],
            payload={"source_event_id": str(event.event_id), **dict(event.metadata)},
            generated_at=event.occurred_at,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            metadata={"event_type": event.event_type},
        )
