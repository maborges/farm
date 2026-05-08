import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends
from core.dependencies import get_session

from growth.models import LandingEvento

router = APIRouter(prefix="/growth", tags=["Growth — Landing"])

# ---------------------------------------------------------------------------
# Rate limiter simples em memória: ip_hash -> (contagem, inicio_janela)
# Não é processo-safe com múltiplos workers — aceitável para volume de landing.
# ---------------------------------------------------------------------------
_rate_buckets: dict[str, tuple[int, float]] = {}
_RATE_MAX = 60
_RATE_WINDOW = 60.0  # segundos


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    if ip in _rate_buckets:
        count, window_start = _rate_buckets[ip]
        if now - window_start > _RATE_WINDOW:
            _rate_buckets[ip] = (1, now)
            return False
        if count >= _RATE_MAX:
            return True
        _rate_buckets[ip] = (count + 1, window_start)
    else:
        _rate_buckets[ip] = (1, now)
    return False


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:32]


def _infer_device(user_agent: str | None) -> str:
    if not user_agent:
        return "unknown"
    ua = user_agent.lower()
    if any(k in ua for k in ("mobile", "android", "iphone", "ipad", "ipod")):
        return "mobile"
    return "desktop"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LandingEventoPayload(BaseModel):
    sessao_id: str
    evento: str
    device: str | None = None
    utm_source: str | None = None
    utm_campaign: str | None = None
    utm_medium: str | None = None
    headline_variant: str | None = None
    path: str | None = None


class VariantMetrics(BaseModel):
    visitas: int
    cta_clicks: int
    conversion_rate: float


class LandingMetrics(BaseModel):
    visitas: int
    cta_clicks: int
    conversion_rate: float
    por_variant: dict[str, VariantMetrics]
    periodo_dias: int
    gerado_em: datetime


# ---------------------------------------------------------------------------
# POST /growth/events — público, sem autenticação
# ---------------------------------------------------------------------------

@router.post("/events", status_code=204)
async def registrar_evento(
    payload: LandingEventoPayload,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    client_ip = request.client.host if request.client else "0.0.0.0"
    ip_hash = _hash_ip(client_ip)

    if _is_rate_limited(ip_hash):
        return Response(status_code=429)

    user_agent = request.headers.get("user-agent")
    device = payload.device or _infer_device(user_agent)

    evento = LandingEvento(
        sessao_id=payload.sessao_id[:100],
        evento=payload.evento[:60],
        device=device[:20] if device else None,
        utm_source=payload.utm_source[:100] if payload.utm_source else None,
        utm_campaign=payload.utm_campaign[:100] if payload.utm_campaign else None,
        utm_medium=payload.utm_medium[:100] if payload.utm_medium else None,
        headline_variant=payload.headline_variant[:5] if payload.headline_variant else None,
        path=payload.path[:200] if payload.path else None,
        ip_hash=ip_hash,
        user_agent=user_agent[:500] if user_agent else None,
    )
    session.add(evento)
    await session.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# GET /growth/events/metrics — agrega métricas por variant
# ---------------------------------------------------------------------------

_EVENTOS_CTA = {"cta_click", "cta_test_click", "cta_demo_click", "plan_select"}

@router.get("/events/metrics", response_model=LandingMetrics)
async def obter_metricas(
    periodo_dias: int = 30,
    session: AsyncSession = Depends(get_session),
) -> Any:
    desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)

    # Total de visitas
    q_visitas = await session.execute(
        select(func.count()).where(
            and_(LandingEvento.evento == "landing_view", LandingEvento.created_at >= desde)
        )
    )
    total_visitas = q_visitas.scalar() or 0

    # Total de cliques CTA
    q_cta = await session.execute(
        select(func.count()).where(
            and_(LandingEvento.evento.in_(_EVENTOS_CTA), LandingEvento.created_at >= desde)
        )
    )
    total_cta = q_cta.scalar() or 0

    conversion_rate = round((total_cta / total_visitas * 100), 2) if total_visitas > 0 else 0.0

    # Métricas por variant (A, B, C)
    por_variant: dict[str, VariantMetrics] = {}
    for variant in ("A", "B", "C"):
        q_v = await session.execute(
            select(func.count()).where(
                and_(
                    LandingEvento.evento == "landing_view",
                    LandingEvento.headline_variant == variant,
                    LandingEvento.created_at >= desde,
                )
            )
        )
        v_visitas = q_v.scalar() or 0

        q_c = await session.execute(
            select(func.count()).where(
                and_(
                    LandingEvento.evento.in_(_EVENTOS_CTA),
                    LandingEvento.headline_variant == variant,
                    LandingEvento.created_at >= desde,
                )
            )
        )
        v_cta = q_c.scalar() or 0

        por_variant[variant] = VariantMetrics(
            visitas=v_visitas,
            cta_clicks=v_cta,
            conversion_rate=round((v_cta / v_visitas * 100), 2) if v_visitas > 0 else 0.0,
        )

    return LandingMetrics(
        visitas=total_visitas,
        cta_clicks=total_cta,
        conversion_rate=conversion_rate,
        por_variant=por_variant,
        periodo_dias=periodo_dias,
        gerado_em=datetime.now(timezone.utc),
    )
