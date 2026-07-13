"""Rotas do provider climático OpenWeather."""

# ruff: noqa: B008, E501, I001

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_tenant_permission
from integracoes.openweather.schemas import (
    OpenWeatherConfigResponse,
    OpenWeatherConfigUpsert,
    OpenWeatherHealthResponse,
    OpenWeatherIntegrationJobResponse,
    OpenWeatherOperationalDiagnosisResponse,
    OpenWeatherStatusResponse,
    OpenWeatherTimelineItemResponse,
    OpenWeatherTestConnectionResponse,
    OpenWeatherWeatherSnapshotResponse,
)
from integracoes.openweather.services import OpenWeatherService

router = APIRouter(prefix="/openweather", tags=["Integração OpenWeather"])


def get_openweather_service(db: AsyncSession = Depends(get_session)) -> OpenWeatherService:
    """Dependency de serviço do provider OpenWeather."""

    return OpenWeatherService(db)


def _translate_domain_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    status_code = (
        404 if "não configurado" in message.lower() or "não encontrada" in message.lower() else 400
    )
    return HTTPException(status_code=status_code, detail=message)


@router.get(
    "/config",
    response_model=OpenWeatherConfigResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_config_openweather(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        config = await service.obter_config_response(str(tenant_id))
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc
    if not config:
        raise HTTPException(status_code=404, detail="OpenWeather não configurado")
    return config


@router.post(
    "/config",
    response_model=OpenWeatherConfigResponse,
    dependencies=[Depends(require_tenant_permission("integrations:configure"))],
)
async def salvar_config_openweather(
    payload: OpenWeatherConfigUpsert,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        return await service.salvar_config(str(tenant_id), payload)
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc


@router.post(
    "/testar-conexao",
    response_model=OpenWeatherTestConnectionResponse,
    dependencies=[Depends(require_tenant_permission("integrations:test"))],
)
async def testar_conexao_openweather(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        return await service.testar_conexao(str(tenant_id))
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc


@router.get(
    "/status",
    response_model=OpenWeatherStatusResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_status_openweather(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        return await service.obter_status_detalhado(str(tenant_id))
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc


@router.get(
    "/health",
    response_model=OpenWeatherHealthResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_health_openweather(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        return await service.obter_health_detalhado(str(tenant_id))
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc


@router.get(
    "/jobs",
    response_model=list[OpenWeatherIntegrationJobResponse],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_jobs_openweather(
    limit: int = 20,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        return await service.listar_jobs(str(tenant_id), limit=limit)
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc


@router.get(
    "/timeline",
    response_model=list[OpenWeatherTimelineItemResponse],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_timeline_openweather(
    status: str | None = None,
    feature_code: str | None = None,
    origem: str | None = None,
    limit: int = 50,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        return await service.listar_timeline_operacional(
            str(tenant_id),
            status=status,
            feature_code=feature_code,
            origem=origem,
            limit=limit,
        )
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc


@router.get(
    "/diagnostico",
    response_model=OpenWeatherOperationalDiagnosisResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_diagnostico_openweather(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        return await service.obter_diagnostico_operacional(str(tenant_id))
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc


@router.post(
    "/sync/current-weather",
    response_model=OpenWeatherWeatherSnapshotResponse,
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def sincronizar_clima_atual(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: OpenWeatherService = Depends(get_openweather_service),
):
    try:
        return await service.sincronizar_clima_atual(str(tenant_id))
    except ValueError as exc:
        raise _translate_domain_error(exc) from exc
