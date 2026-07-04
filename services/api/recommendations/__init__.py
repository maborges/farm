"""Canonical global recommendation engine foundation."""

from .engine import (
    RecommendationEngine,
    RecommendationEngineExecution,
    RecommendationEngineResult,
)
from .enums import (
    ACTIVE_RECOMMENDATION_STATUSES,
    RecommendationActionType,
    RecommendationDomain,
    RecommendationLifecycleActionType,
    RecommendationPriority,
    RecommendationSourceType,
    RecommendationStatus,
)
from .lifecycle_service import RecommendationLifecycleService
from .metrics_service import RecommendationMetricsService
from .models import RecommendationLifecycleEvent, RecommendationResult
from .query_service import RecommendationQueryService
from .provider import RecommendationProvider
from .registry import (
    RecommendationProviderRegistry,
    recommendation_provider_registry,
    register_recommendation_provider,
)
from .runner import RecommendationExecutionRunner
from .scheduler import (
    RecommendationSchedulerExecution,
    RecommendationSchedulerResult,
    RecommendationSchedulerService,
    run_scheduled_recommendations,
)
from .router import router
from .providers import (
    DEFAULT_RECOMMENDATION_PROVIDERS,
    ClimaRecommendationProvider,
    AgriculturaRecommendationProvider,
    FinanceiroRecommendationProvider,
    PecuariaRecommendationProvider,
    EstoqueRecommendationProvider,
    FrotaRecommendationProvider,
    ESGRecommendationProvider,
    WizardRecommendationProvider,
    CampoRecommendationProvider,
    register_default_recommendation_providers,
)
from .schemas import (
    RecommendationDomainMetricsListResponse,
    RecommendationDomainMetricsResponse,
    OperationalContext,
    RecommendationDismissRequest,
    RecommendationCandidate,
    RecommendationExecuteRequest,
    RecommendationMetricsFilterResponse,
    RecommendationLifecycleEventCreate,
    RecommendationLifecycleEventResponse,
    RecommendationLifecycleMetricsResponse,
    RecommendationMetricsSummaryResponse,
    RecommendationMetricsTimelinePointResponse,
    RecommendationEngineRunExecutionResponse,
    RecommendationEngineRunResultResponse,
    RecommendationPostponeRequest,
    RecommendationResultCreate,
    RecommendationResultResponse,
    RecommendationRuleMetricsItem,
    RecommendationRuleMetricsResponse,
    RecommendationSignal,
)

__all__ = [
    "ACTIVE_RECOMMENDATION_STATUSES",
    "OperationalContext",
    "RecommendationActionType",
    "RecommendationCandidate",
    "RecommendationDomain",
    "RecommendationEngine",
    "RecommendationEngineExecution",
    "RecommendationEngineResult",
    "RecommendationEngineRunExecutionResponse",
    "RecommendationEngineRunResultResponse",
    "RecommendationExecutionRunner",
    "RecommendationLifecycleActionType",
    "RecommendationLifecycleEvent",
    "RecommendationLifecycleEventCreate",
    "RecommendationLifecycleEventResponse",
    "RecommendationLifecycleService",
    "RecommendationMetricsService",
    "RecommendationPriority",
    "RecommendationProvider",
    "RecommendationProviderRegistry",
    "RecommendationQueryService",
    "RecommendationResult",
    "RecommendationResultCreate",
    "RecommendationResultResponse",
    "RecommendationMetricsFilterResponse",
    "RecommendationMetricsSummaryResponse",
    "RecommendationDomainMetricsListResponse",
    "RecommendationDomainMetricsResponse",
    "RecommendationLifecycleMetricsResponse",
    "RecommendationMetricsTimelinePointResponse",
    "RecommendationRuleMetricsItem",
    "RecommendationRuleMetricsResponse",
    "RecommendationSignal",
    "RecommendationSourceType",
    "RecommendationStatus",
    "RecommendationSchedulerExecution",
    "RecommendationSchedulerResult",
    "RecommendationSchedulerService",
    "DEFAULT_RECOMMENDATION_PROVIDERS",
    "ClimaRecommendationProvider",
    "AgriculturaRecommendationProvider",
    "FinanceiroRecommendationProvider",
    "PecuariaRecommendationProvider",
    "EstoqueRecommendationProvider",
    "FrotaRecommendationProvider",
    "ESGRecommendationProvider",
    "WizardRecommendationProvider",
    "CampoRecommendationProvider",
    "RecommendationDismissRequest",
    "RecommendationExecuteRequest",
    "RecommendationPostponeRequest",
    "router",
    "recommendation_provider_registry",
    "register_default_recommendation_providers",
    "register_recommendation_provider",
    "run_scheduled_recommendations",
]

register_default_recommendation_providers()
