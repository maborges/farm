from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity
from alert_engine.schemas import AlertListResponse, AlertSummary
from alert_engine.service import AlertLifecycleService
from core.dependencies import get_session, get_tenant_id

router = APIRouter(prefix="/alerts", tags=["Alert Engine"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    domain: Domain | None = Query(default=None),
    category: Category | None = Query(default=None),
    severity: Severity | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> AlertListResponse:
    service = AlertLifecycleService(session, tenant_id)
    result = await service.list_alerts(
        domain=domain,
        category=category,
        severity=severity,
        priority=priority,
        status=status,
        source_type=source_type,
        source_id=source_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return AlertListResponse(items=result.alerts, total=result.total, limit=result.limit, offset=result.offset)


@router.get("/summary", response_model=AlertSummary)
async def get_alert_summary(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    domain: Domain | None = Query(default=None),
    category: Category | None = Query(default=None),
    severity: Severity | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
) -> AlertSummary:
    service = AlertLifecycleService(session, tenant_id)
    return await service.get_alert_summary(
        domain=domain,
        category=category,
        severity=severity,
        priority=priority,
        status=status,
        source_type=source_type,
        source_id=source_id,
        date_from=date_from,
        date_to=date_to,
        top_limit=limit,
    )
