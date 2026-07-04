from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal


def tenant_signal_ids(
    signals: list[RecommendationSignal],
    tenant_id: UUID,
) -> list[UUID]:
    return [signal.signal_id for signal in signals if signal.tenant_id == tenant_id]


def stable_dedupe_key(
    provider_name: str,
    tenant_id: UUID,
    scope_id: str,
    rule_code: str,
    unidade_produtiva_id: UUID | None = None,
) -> str:
    unidade = str(unidade_produtiva_id) if unidade_produtiva_id is not None else "tenant"
    return f"{provider_name}:{tenant_id}:{unidade}:{scope_id}:{rule_code}"


def build_route_target(base_path: str, entity_id: UUID | None = None) -> str:
    if entity_id is None:
        return base_path
    separator = "&" if "?" in base_path else "?"
    return f"{base_path}{separator}id={entity_id}"


def build_candidate_context(
    context: OperationalContext,
    extra: dict[str, object],
) -> dict[str, object]:
    return {
        **extra,
        "generated_at": context.generated_at.isoformat(),
    }


def clamp_confidence(value: float) -> Decimal:
    normalized = max(0.0, min(1.0, value))
    return Decimal(str(round(normalized, 3)))
