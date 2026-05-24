from __future__ import annotations

from contextvars import ContextVar, Token
from datetime import date
from typing import Any, Awaitable, Callable, TypeVar

from loguru import logger

from core.services.analytics_taxonomy import normalizar_severidade

T = TypeVar("T")

_ANALYTICS_CACHE: ContextVar[dict[str, Any] | None] = ContextVar("agrosaas_analytics_request_cache", default=None)


def activate_analytics_request_cache() -> Token[dict[str, Any] | None]:
    """Inicializa um cache novo para a request atual."""
    return _ANALYTICS_CACHE.set({})


def reset_analytics_request_cache(token: Token[dict[str, Any] | None] | None = None) -> None:
    """Restaura o cache da request ou limpa o contexto corrente."""
    if token is not None:
        _ANALYTICS_CACHE.reset(token)
        return
    _ANALYTICS_CACHE.set(None)


def clear_analytics_request_cache() -> None:
    """Limpa o cache corrente sem tentar restaurar estado anterior."""
    _ANALYTICS_CACHE.set(None)


def get_analytics_request_cache() -> dict[str, Any]:
    cache = _ANALYTICS_CACHE.get()
    if cache is None:
        cache = {}
        _ANALYTICS_CACHE.set(cache)
    return cache


def build_analytics_scope_key(
    tenant_id,
    safra_id,
    production_unit_id,
    unidade_produtiva_id,
    data_inicio: date | None,
    data_fim: date | None,
) -> str:
    """Cria chave determinística do escopo analítico da request."""
    return "|".join(
        [
            f"tenant={tenant_id}",
            f"safra={safra_id or '_'}",
            f"production_unit={production_unit_id or '_'}",
            f"unidade_produtiva={unidade_produtiva_id or '_'}",
            f"data_inicio={data_inicio.isoformat() if data_inicio else '_'}",
            f"data_fim={data_fim.isoformat() if data_fim else '_'}",
        ]
    )


def build_analytics_value_key(service_name: str, scope_key: str, variant: str | None = None) -> str:
    parts = [service_name, scope_key]
    if variant:
        parts.append(variant)
    return "||".join(parts)


def build_dre_kpi_cache_key(dre, *, area_total_ha: float, warnings) -> str:
    warnings_key = ",".join(
        sorted(f"{warning.codigo}:{normalizar_severidade(warning.severidade)}" for warning in warnings or [])
    )
    scope_key = build_analytics_scope_key(
        dre.tenant_id,
        dre.safra_id,
        dre.production_unit_id,
        dre.unidade_produtiva_id,
        getattr(dre, "data_inicio", None),
        getattr(dre, "data_fim", None),
    )
    return build_analytics_value_key("agricola.dre.kpi.v1", scope_key, f"area={round(float(area_total_ha), 4)}|warnings={warnings_key}")


async def memoize_request_async(
    service_name: str,
    scope_key: str,
    factory: Callable[[], Awaitable[T]],
) -> T:
    cache = get_analytics_request_cache()
    cache_key = build_analytics_value_key(service_name, scope_key)
    if cache_key in cache:
        logger.bind(component="analytics_cache", service=service_name, scope_key=scope_key).debug("analytics_cache_hit")
        return cache[cache_key]

    logger.bind(component="analytics_cache", service=service_name, scope_key=scope_key).debug("analytics_cache_miss")
    value = await factory()
    cache[cache_key] = value
    return value


def memoize_request_value(
    service_name: str,
    scope_key: str,
    factory: Callable[[], T],
) -> T:
    cache = get_analytics_request_cache()
    cache_key = build_analytics_value_key(service_name, scope_key)
    if cache_key in cache:
        logger.bind(component="analytics_cache", service=service_name, scope_key=scope_key).debug("analytics_cache_hit")
        return cache[cache_key]

    logger.bind(component="analytics_cache", service=service_name, scope_key=scope_key).debug("analytics_cache_miss")
    value = factory()
    cache[cache_key] = value
    return value
