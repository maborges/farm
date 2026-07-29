from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_session, get_tenant_id
from core.schemas.pagination import PaginatedResponse

from .enums import RecommendationDomain, RecommendationPriority, RecommendationStatus
from .authorization import RecommendationAuthorizationService
from .lifecycle_service import RecommendationLifecycleService
from .metrics_service import RecommendationMetricsService
from .query_service import RecommendationQueryService
from .schemas import (
    RecommendationDomainMetricsListResponse,
    RecommendationDismissRequest,
    RecommendationExecuteRequest,
    RecommendationLifecycleMetricsResponse,
    RecommendationMetricsSummaryResponse,
    RecommendationPostponeRequest,
    RecommendationResultResponse,
    RecommendationRuleMetricsResponse,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _authorization(tenant_id: UUID, session: AsyncSession, current_user) -> RecommendationAuthorizationService:
    return RecommendationAuthorizationService(session, tenant_id, current_user.id)


@router.get("", response_model=PaginatedResponse[RecommendationResultResponse])
async def list_recommendations(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    domain: str | None = Query(default=None),
    status_filter: RecommendationStatus | None = Query(default=None, alias="status"),
    priority: RecommendationPriority | None = Query(default=None),
    unidade_produtiva_id: UUID | None = Query(default=None),
    scope_type: str | None = Query(default=None),
    scope_id: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    scope = await _authorization(tenant_id, session, current_user).read_scope()
    service = RecommendationQueryService(session, tenant_id)
    return await service.list_recommendations(
        domain=domain,
        status=status_filter.value if status_filter else None,
        priority=priority.value if priority else None,
        unidade_produtiva_id=unidade_produtiva_id,
        scope_type=scope_type,
        scope_id=scope_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        authorized_unit_ids=scope.unit_ids,
        allow_tenant_wide=scope.allow_tenant_wide,
        allow_all_units=scope.allow_all_units,
    )


@router.get("/{recommendation_id}", response_model=RecommendationResultResponse)
async def get_recommendation(
    recommendation_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
) -> RecommendationResultResponse:
    await _authorization(tenant_id, session, current_user).authorize(recommendation_id, "view")
    service = RecommendationQueryService(session, tenant_id)
    return await service.get_recommendation(recommendation_id)


def _lifecycle_service(
    tenant_id: UUID,
    session: AsyncSession,
) -> RecommendationLifecycleService:
    return RecommendationLifecycleService(session, tenant_id)


def _metrics_service(tenant_id: UUID, session: AsyncSession) -> RecommendationMetricsService:
    return RecommendationMetricsService(session, tenant_id)


@router.get("/metrics/summary", response_model=RecommendationMetricsSummaryResponse)
async def recommendation_metrics_summary(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    domain: RecommendationDomain | None = Query(default=None),
    unidade_produtiva_id: UUID | None = Query(default=None),
) -> RecommendationMetricsSummaryResponse:
    await _authorization(tenant_id, session, current_user).authorize_metrics()
    return await _metrics_service(tenant_id, session).summary(
        start_date=start_date,
        end_date=end_date,
        domain=domain,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/metrics/by-domain", response_model=RecommendationDomainMetricsListResponse)
async def recommendation_metrics_by_domain(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    domain: RecommendationDomain | None = Query(default=None),
    unidade_produtiva_id: UUID | None = Query(default=None),
) -> RecommendationDomainMetricsListResponse:
    await _authorization(tenant_id, session, current_user).authorize_metrics()
    return await _metrics_service(tenant_id, session).by_domain(
        start_date=start_date,
        end_date=end_date,
        domain=domain,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/metrics/by-rule", response_model=RecommendationRuleMetricsResponse)
async def recommendation_metrics_by_rule(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    domain: RecommendationDomain | None = Query(default=None),
    unidade_produtiva_id: UUID | None = Query(default=None),
) -> RecommendationRuleMetricsResponse:
    await _authorization(tenant_id, session, current_user).authorize_metrics()
    return await _metrics_service(tenant_id, session).by_rule(
        start_date=start_date,
        end_date=end_date,
        domain=domain,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/metrics/lifecycle", response_model=RecommendationLifecycleMetricsResponse)
async def recommendation_metrics_lifecycle(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    domain: RecommendationDomain | None = Query(default=None),
    unidade_produtiva_id: UUID | None = Query(default=None),
) -> RecommendationLifecycleMetricsResponse:
    await _authorization(tenant_id, session, current_user).authorize_metrics()
    return await _metrics_service(tenant_id, session).lifecycle(
        start_date=start_date,
        end_date=end_date,
        domain=domain,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.post("/{recommendation_id}/view", response_model=RecommendationResultResponse)
async def view_recommendation(
    recommendation_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
) -> RecommendationResultResponse:
    await _authorization(tenant_id, session, current_user).authorize(recommendation_id, "view")
    service = _lifecycle_service(tenant_id, session)
    recommendation = await service.mark_viewed(recommendation_id, getattr(current_user, "id", None))
    return RecommendationResultResponse.model_validate(recommendation, from_attributes=True)


@router.post("/{recommendation_id}/accept", response_model=RecommendationResultResponse)
async def accept_recommendation(
    recommendation_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
) -> RecommendationResultResponse:
    await _authorization(tenant_id, session, current_user).authorize(recommendation_id, "accept")
    service = _lifecycle_service(tenant_id, session)
    recommendation = await service.accept(recommendation_id, getattr(current_user, "id", None))
    return RecommendationResultResponse.model_validate(recommendation, from_attributes=True)


@router.post("/{recommendation_id}/dismiss", response_model=RecommendationResultResponse)
async def dismiss_recommendation(
    recommendation_id: UUID,
    payload: RecommendationDismissRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
) -> RecommendationResultResponse:
    await _authorization(tenant_id, session, current_user).authorize(recommendation_id, "dismiss")
    service = _lifecycle_service(tenant_id, session)
    recommendation = await service.dismiss(
        recommendation_id,
        getattr(current_user, "id", None),
        reason=payload.reason,
    )
    return RecommendationResultResponse.model_validate(recommendation, from_attributes=True)


@router.post("/{recommendation_id}/postpone", response_model=RecommendationResultResponse)
async def postpone_recommendation(
    recommendation_id: UUID,
    payload: RecommendationPostponeRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
) -> RecommendationResultResponse:
    await _authorization(tenant_id, session, current_user).authorize(recommendation_id, "postpone")
    service = _lifecycle_service(tenant_id, session)
    recommendation = await service.postpone(
        recommendation_id,
        payload.until,
        getattr(current_user, "id", None),
        reason=payload.reason,
    )
    return RecommendationResultResponse.model_validate(recommendation, from_attributes=True)


@router.post("/{recommendation_id}/execute", response_model=RecommendationResultResponse)
async def execute_recommendation(
    recommendation_id: UUID,
    payload: RecommendationExecuteRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
) -> RecommendationResultResponse:
    await _authorization(tenant_id, session, current_user).authorize(recommendation_id, "execute")
    service = _lifecycle_service(tenant_id, session)
    recommendation = await service.execute(
        recommendation_id,
        getattr(current_user, "id", None),
        execution_note=payload.execution_note,
    )
    return RecommendationResultResponse.model_validate(recommendation, from_attributes=True)


@router.post("/{recommendation_id}/reopen", response_model=RecommendationResultResponse)
async def reopen_recommendation(
    recommendation_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
) -> RecommendationResultResponse:
    await _authorization(tenant_id, session, current_user).authorize(recommendation_id, "reopen")
    service = _lifecycle_service(tenant_id, session)
    recommendation = await service.reopen(recommendation_id, getattr(current_user, "id", None))
    return RecommendationResultResponse.model_validate(recommendation, from_attributes=True)
