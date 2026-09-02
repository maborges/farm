"""Endpoints internos que orquestram a integração com TARA."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_tenant_permission

from .client import TaraApiError
from .schemas import TaraClientRegistration, TaraConfigResponse, TaraConfigUpsert, TaraOrderCreate, TaraWeighingPage
from .service import TaraNotConfigured, get_config, resolve_client, save_config, sync_weighings

router = APIRouter(prefix="/tara", tags=["Integração TARA"])


def _error(exc: TaraApiError | TaraNotConfigured) -> HTTPException:
    return HTTPException(status_code=exc.status_code if isinstance(exc, TaraApiError) else 409, detail=exc.detail if isinstance(exc, TaraApiError) else str(exc))


@router.get("/config", response_model=TaraConfigResponse, dependencies=[Depends(require_tenant_permission("integrations:view"))])
async def read_config(tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> TaraConfigResponse:
    config = await get_config(db, str(tenant_id))
    if not config:
        raise HTTPException(404, "TARA não configurada")
    return config


@router.put("/config", response_model=TaraConfigResponse, dependencies=[Depends(require_tenant_permission("integrations:configure"))])
async def write_config(payload: TaraConfigUpsert, tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> TaraConfigResponse:
    return await save_config(db, str(tenant_id), payload)


@router.post("/clients", dependencies=[Depends(require_tenant_permission("integrations:configure"))])
async def register_client(payload: TaraClientRegistration, tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).register_client(payload.model_dump(mode="json"))
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.post("/orders", dependencies=[Depends(require_tenant_permission("balanca:write"))])
async def create_order(payload: TaraOrderCreate, tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).create_order(payload.model_dump(mode="json"))
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.get("/orders/{order_id}", dependencies=[Depends(require_tenant_permission("balanca:read"))])
async def read_order(order_id: str, tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).get_order(order_id)
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.get("/weighings", response_model=TaraWeighingPage, dependencies=[Depends(require_tenant_permission("balanca:read"))])
async def read_weighings(limit: int = Query(100, ge=1, le=100), cursor: str | None = None, tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).list_weighings(limit, cursor)
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.get("/events", dependencies=[Depends(require_tenant_permission("balanca:read"))])
async def read_events(limit: int = Query(100, ge=1, le=100), cursor: str | None = None, tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).list_events(limit, cursor)
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.post("/weighings/sync", dependencies=[Depends(require_tenant_permission("balanca:read"))])
async def sync_tara_weighings(limit: int = Query(100, ge=1, le=100), tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    try:
        return {"items": await sync_weighings(db, str(tenant_id), limit)}
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.get("/webhooks", dependencies=[Depends(require_tenant_permission("balanca:read"))])
async def read_webhook(tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).get_webhook()
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.put("/webhooks", dependencies=[Depends(require_tenant_permission("balanca:configure"))])
async def write_webhook(payload: dict[str, Any], tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).manage_webhook(payload)
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.post("/webhooks/replay", dependencies=[Depends(require_tenant_permission("balanca:configure"))])
async def replay_webhook(payload: dict[str, Any], tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).replay_webhook(payload)
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc


@router.post("/stations/activate", dependencies=[Depends(require_tenant_permission("balanca:configure"))])
async def activate_station(payload: dict[str, Any], tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)) -> Any:
    try:
        return await (await resolve_client(db, str(tenant_id))).activate_station(payload)
    except (TaraApiError, TaraNotConfigured) as exc:
        raise _error(exc) from exc
