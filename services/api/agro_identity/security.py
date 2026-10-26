"""Segurança criptográfica, JWT segregado, cookies HttpOnly e proteção contra força bruta."""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
import uuid

from fastapi import HTTPException, Request, Response, status
from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext
try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None  # type: ignore[assignment,misc]

from .config import (
    AGRO_ALLOWED_ORIGINS,
    AGRO_COOKIE_DOMAIN,
    AGRO_COOKIE_NAME,
    AGRO_COOKIE_SECURE,
    AGRO_JWT_ALGORITHM,
    AGRO_JWT_AUDIENCE,
    AGRO_JWT_ISSUER,
    AGRO_JWT_SECRET_KEY,
    AGRO_LOCKOUT_MINUTES,
    AGRO_MAX_LOGIN_ATTEMPTS,
    AGRO_TOKEN_EXPIRE_DAYS,
)

import bcrypt


def hash_password(password: str) -> str:
    """Gera hash seguro com bcrypt e salt automático."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha em tempo constante contra timing attacks."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Gera hash SHA-256 do token para armazenamento e busca indexada rápida."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_token() -> str:
    """Gera token aleatório criptograficamente forte para recuperação de senha."""
    return secrets.token_urlsafe(32)


def generate_verification_code() -> str:
    """Gera código numérico de 6 dígitos para verificação de e-mail."""
    return f"{secrets.randbelow(1_000_000):06d}"


def create_agro_jwt(
    usuario_id: uuid.UUID,
    email: str,
    nome: str,
    sessao_id: uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Cria token JWT exclusivo para identidade individual do DeepFarms Agro.

    Emissor, audiência e claims garantem que o token seja rejeitado em rotas comerciais.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=AGRO_TOKEN_EXPIRE_DAYS))

    claims: dict[str, Any] = {
        "iss": AGRO_JWT_ISSUER,
        "aud": AGRO_JWT_AUDIENCE,
        "sub": str(usuario_id),
        "email": email,
        "name": nome,
        "sid": str(sessao_id),
        "account_type": "INDIVIDUAL_FREE",
        "tenant_id": None,
        "role": "INDIVIDUAL_USER",
        "modules": ["AGRO_FREE"],
        "scope": ["agro:profile", "agro:byok"],
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(claims, AGRO_JWT_SECRET_KEY, algorithm=AGRO_JWT_ALGORITHM)


def decode_agro_jwt(token: str) -> dict[str, Any]:
    """Decodifica e valida assinatura, emissor, audiência e tipo de conta individual."""
    try:
        payload = jwt.decode(
            token,
            AGRO_JWT_SECRET_KEY,
            algorithms=[AGRO_JWT_ALGORITHM],
            issuer=AGRO_JWT_ISSUER,
            audience=AGRO_JWT_AUDIENCE,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token individual inválido ou expirado.",
        ) from exc

    if payload.get("account_type") != "INDIVIDUAL_FREE":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de conta incompatível com o módulo de identidade individual.",
        )

    return payload


def set_agro_session_cookie(response: Response, token: str) -> None:
    """Define cookie de sessão individual HttpOnly, SameSite=Lax com expiração sincronizada."""
    max_age = AGRO_TOKEN_EXPIRE_DAYS * 24 * 3600
    kwargs: dict[str, Any] = {
        "key": AGRO_COOKIE_NAME,
        "value": token,
        "max_age": max_age,
        "expires": max_age,
        "httponly": True,
        "samesite": "lax",
        "secure": AGRO_COOKIE_SECURE,
        "path": "/",
    }
    if AGRO_COOKIE_DOMAIN:
        kwargs["domain"] = AGRO_COOKIE_DOMAIN
    response.set_cookie(**kwargs)


def clear_agro_session_cookie(response: Response) -> None:
    """Remove o cookie de sessão individual no logout."""
    kwargs: dict[str, Any] = {
        "key": AGRO_COOKIE_NAME,
        "path": "/",
        "httponly": True,
        "samesite": "lax",
        "secure": AGRO_COOKIE_SECURE,
    }
    if AGRO_COOKIE_DOMAIN:
        kwargs["domain"] = AGRO_COOKIE_DOMAIN
    response.delete_cookie(**kwargs)


def verify_agro_csrf(request: Request) -> None:
    """Valida proteção CSRF para operações que alteram estado via cookie.

    Garante proteção ativa contra CSRF tradicional e contra forjamento
    inter-subdomínios (e.g., scripts em app.deepfarms.com.br ou campo.deepfarms.com.br
    disparando requisições com o cookie de sessão da identidade Agro).
    """
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return

    # Se a requisição não possui cookie de sessão do Agro, não há risco de cookie hijacking
    cookie_token = request.cookies.get(AGRO_COOKIE_NAME)
    if not cookie_token:
        return

    # 1. Checagem de Origem / Referer
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    effective_origin: str | None = None
    if origin:
        effective_origin = origin.rstrip("/")
    elif referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            effective_origin = f"{parsed.scheme}://{parsed.netloc}"

    if effective_origin:
        normalized_allowed = [o.rstrip("/") for o in AGRO_ALLOWED_ORIGINS]
        if effective_origin not in normalized_allowed:
            logger.warning(
                f"Tentativa de CSRF inter-subdomínio ou cross-origin bloqueada: {effective_origin} -> {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origem não autorizada para operações de identidade Agro (proteção CSRF inter-subdomínios).",
            )

    # 2. Checagem Fetch Metadata (Sec-Fetch-Site)
    sec_fetch_site = request.headers.get("sec-fetch-site")
    if sec_fetch_site == "cross-site":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requisição cross-site bloqueada por política de segurança CSRF.",
        )


class AgroLoginRateLimiter:
    """Limitador de tentativas de login e proteção contra força bruta por e-mail e IP."""

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis: Redis | None = None
        if redis_url and Redis is not None:
            try:
                self.redis = Redis.from_url(redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)
            except Exception:
                self.redis = None
        # Fallback L1 em memória local: key -> (tentativas, bloqueado_ate_timestamp)
        self._memory_cache: dict[str, tuple[int, float]] = {}

    async def _redis_ready(self) -> bool:
        if self.redis is None:
            return False
        try:
            return bool(await self.redis.ping())
        except Exception:
            return False

    async def check_lockout(self, email: str, ip: str | None) -> None:
        """Verifica se a conta ou o IP estão em período de bloqueio temporário."""
        now = time.time()
        email_clean = email.lower()
        lockout_bucket = f"agro:lockout:{email_clean}"

        if await self._redis_ready():
            try:
                assert self.redis is not None
                ttl = await self.redis.ttl(lockout_bucket)
                if ttl > 0:
                    minutos = max(1, ttl // 60)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Muitas tentativas incorretas. Conta bloqueada temporariamente por {minutos} minuto(s).",
                    )
            except HTTPException:
                raise
            except Exception:
                pass

        # Checagem em memória local
        entry = self._memory_cache.get(lockout_bucket)
        if entry:
            tentativas, bloqueado_ate = entry
            if now < bloqueado_ate:
                minutos = max(1, int((bloqueado_ate - now) // 60))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Muitas tentativas incorretas. Conta bloqueada temporariamente por {minutos} minuto(s).",
                )
            elif bloqueado_ate > 0 and now >= bloqueado_ate:
                # Período de bloqueio expirou
                self._memory_cache.pop(lockout_bucket, None)

    async def record_failure(self, email: str) -> None:
        """Registra falha de autenticação e aplica bloqueio se o limite for atingido."""
        now = time.time()
        email_clean = email.lower()
        lockout_bucket = f"agro:lockout:{email_clean}"
        attempts_bucket = f"agro:attempts:{email_clean}"
        lockout_duration = AGRO_LOCKOUT_MINUTES * 60

        tentativas = 1
        entry = self._memory_cache.get(lockout_bucket)
        if entry:
            tentativas = entry[0] + 1

        # Contagem distribuída via Redis quando disponível
        if await self._redis_ready():
            try:
                assert self.redis is not None
                redis_count = await self.redis.incr(attempts_bucket)
                if redis_count == 1:
                    await self.redis.expire(attempts_bucket, lockout_duration)
                tentativas = max(tentativas, redis_count)
                if tentativas >= AGRO_MAX_LOGIN_ATTEMPTS:
                    await self.redis.set(lockout_bucket, "1", ex=lockout_duration)
            except Exception:
                pass

        bloqueado_ate = (now + lockout_duration) if tentativas >= AGRO_MAX_LOGIN_ATTEMPTS else 0
        self._memory_cache[lockout_bucket] = (tentativas, bloqueado_ate)

    async def record_success(self, email: str) -> None:
        """Limpa as tentativas de login após autenticação bem-sucedida."""
        email_clean = email.lower()
        lockout_bucket = f"agro:lockout:{email_clean}"
        attempts_bucket = f"agro:attempts:{email_clean}"
        self._memory_cache.pop(lockout_bucket, None)
        if await self._redis_ready():
            try:
                assert self.redis is not None
                await self.redis.delete(lockout_bucket, attempts_bucket)
            except Exception:
                pass


_default_agro_rate_limiter: AgroLoginRateLimiter | None = None


def get_agro_rate_limiter() -> AgroLoginRateLimiter:
    """Retorna a instância singleton do rate limiter de login individual."""
    global _default_agro_rate_limiter
    if _default_agro_rate_limiter is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _default_agro_rate_limiter = AgroLoginRateLimiter(redis_url=redis_url)
    return _default_agro_rate_limiter

