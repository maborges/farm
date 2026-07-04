from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import EntityNotFoundError
from core.schemas.pagination import PaginatedResponse

from .enums import RecommendationPriority
from .models import RecommendationResult
from .schemas import RecommendationResultResponse


class RecommendationQueryService:
    """Read-only access layer for persisted recommendations."""

    PRIORITY_ORDER = {
        RecommendationPriority.URGENT.value: 4,
        RecommendationPriority.HIGH.value: 3,
        RecommendationPriority.NORMAL.value: 2,
        RecommendationPriority.LOW.value: 1,
    }

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def list_recommendations(
        self,
        *,
        domain: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
        scope_type: str | None = None,
        scope_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResponse[RecommendationResultResponse]:
        """List persisted recommendations with tenant-safe filters.

        Args:
            domain: Optional domain filter.
            status: Optional lifecycle status filter.
            priority: Optional priority filter.
            unidade_produtiva_id: Optional production unit filter.
            scope_type: Optional scope type filter.
            scope_id: Optional scope identifier filter.
            start_date: Optional inclusive start date filter based on recommendation creation date.
            end_date: Optional inclusive end date filter based on recommendation creation date.
            limit: Maximum number of rows to return.
            offset: Pagination offset.

        Returns:
            Paginated response with recommendation items.

        Raises:
            None.
        """
        await self._set_rls_context()
        where_clause = self._build_filters(
            domain,
            status,
            priority,
            unidade_produtiva_id,
            scope_type,
            scope_id,
            start_date,
            end_date,
        )
        total = await self._count(where_clause)
        items = await self._fetch_items(where_clause, limit=limit, offset=offset)
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_recommendation(self, recommendation_id: uuid.UUID) -> RecommendationResultResponse:
        """Fetch a single recommendation by identifier.

        Args:
            recommendation_id: Recommendation primary key.

        Returns:
            The recommendation response model.

        Raises:
            EntityNotFoundError: If the recommendation does not exist for the tenant.
        """
        await self._set_rls_context()
        stmt = select(RecommendationResult).where(
            RecommendationResult.id == recommendation_id,
            RecommendationResult.tenant_id == self.tenant_id,
        )
        recommendation = (await self.session.execute(stmt)).scalars().first()
        if recommendation is None:
            raise EntityNotFoundError(f"Recommendation {recommendation_id} not found.")
        return RecommendationResultResponse.model_validate(recommendation, from_attributes=True)

    async def _count(self, where_clause: list[Any]) -> int:
        stmt = select(func.count(RecommendationResult.id)).where(*where_clause)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _fetch_items(
        self,
        where_clause: list[Any],
        *,
        limit: int,
        offset: int,
    ) -> list[RecommendationResultResponse]:
        stmt = (
            select(RecommendationResult)
            .where(*where_clause)
            .order_by(
                case(self.PRIORITY_ORDER, value=RecommendationResult.priority, else_=0).desc(),
                RecommendationResult.updated_at.desc(),
                RecommendationResult.created_at.desc(),
                RecommendationResult.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [RecommendationResultResponse.model_validate(row, from_attributes=True) for row in rows]

    def _build_filters(
        self,
        domain: str | None,
        status: str | None,
        priority: str | None,
        unidade_produtiva_id: uuid.UUID | None,
        scope_type: str | None,
        scope_id: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[Any]:
        filters: list[Any] = [RecommendationResult.tenant_id == self.tenant_id]
        if domain:
            filters.append(RecommendationResult.domain == domain)
        if status:
            filters.append(RecommendationResult.status == status)
        if priority:
            filters.append(RecommendationResult.priority == priority)
        if unidade_produtiva_id:
            filters.append(RecommendationResult.unidade_produtiva_id == unidade_produtiva_id)
        if scope_type:
            filters.append(RecommendationResult.scope_type == scope_type)
        if scope_id:
            filters.append(RecommendationResult.scope_id == scope_id)
        if start_date:
            filters.append(RecommendationResult.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
        if end_date:
            filters.append(
                RecommendationResult.created_at
                < datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
            )
        return filters

    async def _set_rls_context(self) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(self.tenant_id)},
        )
