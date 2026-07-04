from __future__ import annotations

from ..registry import RecommendationProviderRegistry, recommendation_provider_registry
from ..provider import RecommendationProvider
from .agricultura_provider import AgriculturaRecommendationProvider
from .campo_provider import CampoRecommendationProvider
from .clima_provider import ClimaRecommendationProvider
from .estoque_provider import EstoqueRecommendationProvider
from .esg_provider import ESGRecommendationProvider
from .financeiro_provider import FinanceiroRecommendationProvider
from .frota_provider import FrotaRecommendationProvider
from .pecuaria_provider import PecuariaRecommendationProvider
from .wizard_provider import WizardRecommendationProvider

DEFAULT_RECOMMENDATION_PROVIDERS: tuple[type[RecommendationProvider], ...] = (
    ClimaRecommendationProvider,
    AgriculturaRecommendationProvider,
    FinanceiroRecommendationProvider,
    PecuariaRecommendationProvider,
    EstoqueRecommendationProvider,
    FrotaRecommendationProvider,
    ESGRecommendationProvider,
    WizardRecommendationProvider,
    CampoRecommendationProvider,
)


def register_default_recommendation_providers(
    registry: RecommendationProviderRegistry | None = None,
) -> tuple[type[RecommendationProvider], ...]:
    target_registry = registry or recommendation_provider_registry
    return target_registry.register_many(DEFAULT_RECOMMENDATION_PROVIDERS)


__all__ = [
    "DEFAULT_RECOMMENDATION_PROVIDERS",
    "AgriculturaRecommendationProvider",
    "CampoRecommendationProvider",
    "ClimaRecommendationProvider",
    "EstoqueRecommendationProvider",
    "ESGRecommendationProvider",
    "FinanceiroRecommendationProvider",
    "FrotaRecommendationProvider",
    "PecuariaRecommendationProvider",
    "WizardRecommendationProvider",
    "register_default_recommendation_providers",
]
