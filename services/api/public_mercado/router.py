"""Endpoint PTAX público, sem JWT, tenant, sessão ou dados comerciais."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from core.config import settings
from .cache import PtaxCache
from .ptax import BcbPtaxClient, PtaxResponse
from .service import PtaxService

router = APIRouter(prefix="/public/mercado", tags=["Mercado público"])
service = PtaxService(
    PtaxCache(settings.redis_url, settings.ptax_single_worker_fallback),
    BcbPtaxClient(),
    settings.ptax_cache_ttl_seconds,
)


def get_ptax_service() -> PtaxService:
    return service


@router.get("/ptax", response_model=PtaxResponse)
async def get_public_ptax(
    request: Request,
    response: Response,
    ptax: PtaxService = Depends(get_ptax_service),
) -> PtaxResponse:
    # request.client.host é fornecido por ASGI; X-Forwarded-For só pode ser
    # aceito pelo servidor ASGI quando o proxy emissor for explicitamente confiável.
    address = request.client.host if request.client else "unknown"
    bucket = hashlib.sha256(address.encode()).hexdigest()[:24]
    shared = await ptax.cache.redis_ready()
    if not await ptax.cache.allow_request(bucket, shared):
        if not shared and not ptax.cache.single_worker_fallback:
            raise HTTPException(status_code=503, detail="Cache compartilhado indisponível")
        raise HTTPException(status_code=429, detail="Limite de consultas PTAX excedido")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return await ptax.get(datetime.now(timezone.utc))
