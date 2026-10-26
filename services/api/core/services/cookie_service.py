"""Gerenciamento seguro de cookies de sessão HttpOnly para navegadores e PWA."""

from __future__ import annotations

from typing import Any
from fastapi import Response

from core.config import settings

COOKIE_AGRO = "deepfarms_agro_session"
COOKIE_GLOBAL = "deepfarms_session"
DEFAULT_MAX_AGE = 7 * 24 * 3600  # 7 dias


def set_platform_session_cookie(
    response: Response,
    token: str,
    max_age: int = DEFAULT_MAX_AGE,
) -> None:
    """Define cookies de sessão HttpOnly com SameSite=Lax e flag Secure adequada."""
    is_prod = settings.environment.lower() in ("production", "prod")
    cookie_kwargs: dict[str, Any] = {
        "value": token,
        "max_age": max_age,
        "expires": max_age,
        "httponly": True,
        "samesite": "lax",
        "secure": is_prod,
        "path": "/",
    }
    response.set_cookie(key=COOKIE_AGRO, **cookie_kwargs)
    response.set_cookie(key=COOKIE_GLOBAL, **cookie_kwargs)


def clear_platform_session_cookie(response: Response) -> None:
    """Remove cookies de sessão no logout."""
    is_prod = settings.environment.lower() in ("production", "prod")
    cookie_kwargs: dict[str, Any] = {
        "httponly": True,
        "samesite": "lax",
        "secure": is_prod,
        "path": "/",
    }
    response.delete_cookie(key=COOKIE_AGRO, **cookie_kwargs)
    response.delete_cookie(key=COOKIE_GLOBAL, **cookie_kwargs)
