from __future__ import annotations

from fastapi import Depends, HTTPException, Query, status, Request
from loguru import logger
from jose import JWTError, jwt
from core.config import settings
from typing import TYPE_CHECKING, List, Optional, AsyncGenerator
import uuid
import hashlib
import time
import asyncio
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update
from sqlalchemy.exc import SQLAlchemyError
from core.database import (
    async_session_maker,
    catalog_admin_async_session_maker,
    rls_dev_async_session_maker,
    DB_URL,
)

try:
    from asyncpg.exceptions import TooManyConnectionsError
except Exception:  # pragma: no cover - asyncpg may not be installed in sqlite-only envs
    TooManyConnectionsError = None

# ---------------------------------------------------------------------------
# Cache simples TTL para validação de sessão (evita query por request)
# ---------------------------------------------------------------------------
_SESSION_CACHE: dict[str, tuple[bool, float]] = {}  # token_hash -> (is_valid, expires_at)
_SESSION_CACHE_TTL = settings.session_cache_ttl_seconds
_SESSION_CACHE_MAX = 2000
TENANT_CONTEXT_ERROR = "Contexto de tenant ausente ou inválido. Refaça o login ou selecione o tenant ativo."
PLAN_NOT_CONTRACTED_ERROR = "Seu plano atual não inclui este recurso. Faça upgrade do plano para continuar."
PLAN_INSUFFICIENT_TIER_ERROR = "Seu plano atual não atende ao nível exigido. Faça upgrade do plano para continuar."
PLAN_INACTIVE_ERROR = "Assinatura não encontrada ou inativa. Contrate ou reative um plano para continuar."
PLAN_INVALID_ERROR = "Configuração de plano inválida. Verifique a assinatura contratada."

def _limit_message(resource: str, limite: int | float, atual: int | float, extra: str | None = None) -> str:
    suffix = f" {extra}" if extra else ""
    return (
        f"Seu plano atingiu o limite de {resource}. "
        f"Você tem {atual} de {limite}{suffix}. Faça upgrade do plano para continuar."
    )

def _cache_get(token_hash: str) -> bool | None:
    entry = _SESSION_CACHE.get(token_hash)
    if entry and time.monotonic() < entry[1]:
        return entry[0]
    _SESSION_CACHE.pop(token_hash, None)
    return None

def _cache_set(token_hash: str, is_valid: bool) -> None:
    if len(_SESSION_CACHE) >= _SESSION_CACHE_MAX:
        # Evict oldest ~10%
        to_remove = sorted(_SESSION_CACHE, key=lambda k: _SESSION_CACHE[k][1])[:200]
        for k in to_remove:
            _SESSION_CACHE.pop(k, None)
    _SESSION_CACHE[token_hash] = (is_valid, time.monotonic() + _SESSION_CACHE_TTL)

def invalidate_session_cache(token_hash: str) -> None:
    """Invalida o cache de uma sessão específica (chamar ao revogar)."""
    _SESSION_CACHE.pop(token_hash, None)


async def _activate_session_read_only(session: AsyncSession) -> None:
    """Ativa trava física READ ONLY na transação atual do PostgreSQL."""
    session.info["read_only_transaction"] = True
    bind = getattr(session, "bind", None)
    dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
    if dialect_name == "sqlite":
        return

    if "postgresql" in DB_URL or dialect_name == "postgresql":
        await session.execute(text("SET LOCAL TRANSACTION READ ONLY"))


_READ_ONLY_EXPIRED_ALLOWED_PREFIXES = (
    "/api/v1/auth/me",
    "/api/v1/auth/logout",
    "/api/v1/auth/heartbeat",
    "/api/v1/auth/my-tenants",
    "/api/v1/auth/switch-tenant",
    "/api/v1/sessions/me",
    "/api/v1/support/tickets",
)

_READ_ONLY_RESTRICTED_PREFIXES = (
    "/api/v1/team/users",
    "/api/v1/team/invites",
    "/api/v1/team/stats",
    "/api/v1/team/roles",
    "/api/v1/team/members",
    "/api/v1/sessions/team",
    "/api/v1/audit-log",
    "/api/v1/auth/tenant/usuarios",
    "/api/v1/plan-changes",
    "/api/v1/configuration",
    "/api/v1/integracoes",
    "/api/v1/iot",
    "/api/v1/sankhya",
    "/api/v1/tara",
    "/api/v1/campo",
    "/api/v1/sync",
    "/api/v1/ia",
    "/api/v1/agricola/agronomo/chat",
)


def _is_read_only_restricted_path(path: str) -> bool:
    """Identifica rotas administrativas, de IA paga, dispositivos ou PII proibidas em modo somente consulta."""
    if path.startswith(_READ_ONLY_RESTRICTED_PREFIXES):
        return True
    if path.startswith("/api/v1/billing") and not path.startswith("/api/v1/billing/plans"):
        return True
    if path.startswith("/api/v1/cadastros/pessoas/") and path.endswith(
        ("/pii", "/bancario", "/consentimentos", "/anonimizar")
    ):
        return True
    return False


def _is_read_only_allowed_write(method: str, path: str) -> bool:
    """Libera apenas mutações da própria sessão/senha ou suporte próprio."""
    if method not in ("POST", "PUT", "PATCH", "DELETE"):
        return False
    if path.startswith(("/api/v1/auth/logout", "/api/v1/auth/heartbeat", "/api/v1/auth/switch-tenant")):
        return True
    if path in ("/api/v1/auth/me/change-password", "/api/v1/auth/me/preferences/navigation"):
        return True
    if path == "/api/v1/sessions/me" or path.startswith("/api/v1/sessions/me/"):
        return True
    if path == "/api/v1/support/tickets" or path.startswith("/api/v1/support/tickets/"):
        return True
    return False


async def _validate_and_apply_tenant_membership(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    claims: dict,
    request: Request | None,
) -> None:
    """Valida vínculo ativo, vigência de acesso demo e aplica bloqueios read-only e LGPD."""
    from core.models.auth import PerfilAcesso, TenantUsuario
    from core.models.tenant import Tenant
    from core.services.demo_access_service import is_demo_tenant, is_read_only_profile

    row = (
        await session.execute(
            select(TenantUsuario, PerfilAcesso, Tenant)
            .join(Tenant, Tenant.id == TenantUsuario.tenant_id)
            .outerjoin(PerfilAcesso, PerfilAcesso.id == TenantUsuario.perfil_id)
            .where(
                TenantUsuario.tenant_id == tenant_id,
                TenantUsuario.usuario_id == user_id,
                TenantUsuario.status == "ATIVO",
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

    tu, perfil, tenant = row
    is_read_only = (not tu.is_owner) and is_read_only_profile(perfil)
    is_demo_visitor = is_read_only and (
        is_demo_tenant(tenant) or bool(perfil and getattr(perfil, "is_demo_profile", False))
    )
    is_expired = bool(tu.data_validade_acesso and tu.data_validade_acesso < date.today())
    demo_expired = is_expired and is_demo_visitor

    claims["is_read_only"] = is_read_only
    claims["is_demo_visitor"] = is_demo_visitor
    claims["demo_expired"] = demo_expired
    claims["data_validade_acesso"] = (
        tu.data_validade_acesso.isoformat() if tu.data_validade_acesso else None
    )

    path = str(getattr(getattr(request, "url", None), "path", "")) if request is not None else ""
    method = request.method.upper() if request is not None else "GET"

    if is_expired:
        if not is_demo_visitor:
            raise HTTPException(status_code=403, detail="Seu acesso temporário a este ambiente expirou.")
        if request is not None and not path.startswith(_READ_ONLY_EXPIRED_ALLOWED_PREFIXES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu período de demonstração expirou. Solicite uma prorrogação de +15 dias pelo módulo de Suporte.",
                headers={"X-Error-Code": "DEMO_ACCESS_EXPIRED"},
            )

    if is_read_only and request is not None:
        if _is_read_only_restricted_path(path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Recurso administrativo ou sensível indisponível para perfil de demonstração.",
                headers={"X-Error-Code": "READ_ONLY_RESTRICTED_RESOURCE"},
            )

        allowed_write = _is_read_only_allowed_write(method, path)
        if method in ("POST", "PUT", "PATCH", "DELETE") and not allowed_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil de demonstração somente consulta. Alterações, inclusões, exclusões ou processamentos não são permitidos.",
                headers={"X-Error-Code": "READ_ONLY_PROFILE"},
            )

        if not allowed_write:
            await _activate_session_read_only(session)


async def _activate_session_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Ativa um Tenant já autenticado e autorizado na transação atual."""
    bind = getattr(session, "bind", None)
    dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
    if dialect_name == "sqlite":
        session.info["tenant_id"] = tenant_id
        return

    if "postgresql" in DB_URL or dialect_name == "postgresql":
        try:
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )
        except (asyncio.TimeoutError, OSError, SQLAlchemyError) as exc:
            logger.error(
                "Falha ao ativar contexto Tenant no banco",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Banco de dados indisponível ou pool de conexões esgotado. Tente novamente em instantes.",
            ) from exc
        except Exception as exc:
            if _is_connection_exhaustion_error(exc):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Banco de dados indisponível ou pool de conexões esgotado. Tente novamente em instantes.",
                ) from exc
            raise
    session.info["tenant_id"] = tenant_id


def _is_connection_exhaustion_error(exc: Exception) -> bool:
    """Detecta recusa do Postgres por falta de slots/conexões."""
    if TooManyConnectionsError is not None and isinstance(exc, TooManyConnectionsError):
        return True

    message = str(exc).lower()
    return (
        "remaining connection slots are reserved" in message
        or "too many connections" in message
        or "connection slots" in message
        or type(exc).__name__ == "TooManyConnectionsError"
    )


if TYPE_CHECKING:
    from core.constants import PlanTier

# ==============================================================================
# CORE DEPENDENCIES (Top-level)
# ==============================================================================

RLS_DEV_RESTRICTED_ROUTE_PAIRS = frozenset({
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/notificacoes/"),
    ("GET", "/api/v1/notificacoes/"),
})


def uses_restricted_route_session(request: Request | None) -> bool:
    """Select restricted runtime for approved routes (or all routes when enabled)."""
    if not settings.rls_dev_route_sessions_enabled or request is None:
        return False
    if getattr(settings, "rls_dev_all_routes_enabled", False):
        return True
    return (request.method.upper(), request.url.path) in RLS_DEV_RESTRICTED_ROUTE_PAIRS


async def get_session(request: Request = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Abre sessão sem presumir Tenant. O contexto só é instalado por dependências
    que validam a identidade, a sessão e a autorização de acesso ao Tenant.
    O argumento Request permanece por compatibilidade com chamadas existentes.
    """
    restricted = uses_restricted_route_session(request)
    if restricted:
        if rls_dev_async_session_maker is None:
            # Never fall back to the legacy owner if opt-in restricted routing
            # is enabled but its credentials/engine did not initialize.
            raise RuntimeError("Restricted route session is enabled but unavailable")
        session_maker = rls_dev_async_session_maker
    else:
        session_maker = async_session_maker

    async with session_maker() as session:
        if restricted:
            session.info["rls_dev_restricted_route"] = True
        yield session


async def get_catalog_admin_session(
    request: Request = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Abre sessão dedicada para administração de catálogos globais sob RLS."""
    if catalog_admin_async_session_maker is not None:
        session_maker = catalog_admin_async_session_maker
    elif settings.require_restricted_runtime_role or uses_restricted_route_session(request):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conexão administrativa de catálogo não configurada para escrita global.",
        )
    else:
        session_maker = async_session_maker

    async with session_maker() as session:
        yield session

def _verify_csrf_for_cookie(request: Request) -> None:
    """Valida CSRF quando a requisição é autenticada por cookie e altera estado."""
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return

    sec_fetch_site = request.headers.get("sec-fetch-site")
    if sec_fetch_site == "cross-site":
        logger.warning(
            "CSRF bloqueado por sec-fetch-site cross-site",
            path=str(request.url.path),
            method=request.method,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requisição cross-site bloqueada por política de segurança CSRF.",
        )

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    effective_origin: str | None = None
    if origin:
        effective_origin = origin.rstrip("/")
    elif referer:
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            effective_origin = f"{parsed.scheme}://{parsed.netloc}"

    if effective_origin:
        allowed = {o.rstrip("/") for o in settings.allow_origins}
        if effective_origin not in allowed and not effective_origin.endswith(".deepfarms.com.br"):
            custom_csrf = request.headers.get("X-Agro-CSRF") or request.headers.get("X-Requested-With")
            if not custom_csrf:
                logger.warning(
                    "CSRF bloqueado por origem não autorizada",
                    origin=effective_origin,
                    path=str(request.url.path),
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Origem não autorizada para operações autenticadas por cookie.",
                )


def get_token(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]

    # Cookie fallback (deepfarms_agro_session ou deepfarms_session)
    cookie_token = request.cookies.get("deepfarms_agro_session") or request.cookies.get("deepfarms_session")
    if cookie_token:
        _verify_csrf_for_cookie(request)
        return cookie_token

    logger.warning(
        "Auth header e cookie ausentes ou inválidos",
        path=str(request.url.path),
        method=request.method,
        has_authorization_header=authorization is not None,
        origin=request.headers.get("origin"),
        referer=request.headers.get("referer"),
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado"
    )

def verify_commercial_jwt_guardrail(token: str = Depends(get_token)) -> str:
    """GUARDRAIL MANDATÓRIO: Tokens de identidade individual do DeepFarms Agro (INDIVIDUAL_FREE)

    NUNCA têm permissão para acessar rotas e recursos comerciais do SaaS.
    Rejeita imediatamente com 403 Forbidden ANTES de adquirir qualquer conexão do pool comercial.
    """
    try:
        unverified_claims = jwt.get_unverified_claims(token)
        account_type = unverified_claims.get("account_type")
        scopes = unverified_claims.get("product_scope") or []
        token_version = unverified_claims.get("token_version", 1)
        is_v2 = isinstance(token_version, int) and token_version >= 2
        if (
            account_type == "INDIVIDUAL_FREE"
            or unverified_claims.get("iss") == "deepfarms:agro:auth"
            or (is_v2 and account_type != "PLATFORM_ADMIN" and "saas" not in scopes)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tokens de identidade individual do DeepFarms Agro não possuem acesso aos recursos comerciais do SaaS.",
            )
    except HTTPException:
        raise
    except Exception:
        pass
    return token


def _decode_platform_token(token: str) -> dict:
    """Valida tokens v2 estritamente e mantém leitura temporária de JWTs legados."""
    try:
        unverified = jwt.get_unverified_claims(token)
        options: dict = {}
        decode_kwargs: dict = {}
        token_version = unverified.get("token_version", 1)
        is_v2 = isinstance(token_version, int) and token_version >= 2
        if is_v2:
            decode_kwargs = {
                "issuer": settings.jwt_issuer,
                "audience": settings.jwt_audience,
            }
        else:
            options = {"verify_aud": False, "verify_iss": False}
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options=options,
            **decode_kwargs,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        ) from exc

    token_version = payload.get("token_version", 1)
    if isinstance(token_version, int) and token_version >= 2:
        account_type = payload.get("account_type")
        scopes = payload.get("product_scope")
        if not isinstance(scopes, list) or not scopes:
            raise HTTPException(status_code=401, detail="Token sem escopo de produto")
        if account_type not in {"INDIVIDUAL_FREE", "COMMERCIAL", "PLATFORM_ADMIN"}:
            raise HTTPException(status_code=401, detail="Tipo de conta inválido")
        if account_type == "INDIVIDUAL_FREE" and (
            payload.get("tenant_id") is not None or "agro:free" not in scopes
        ):
            raise HTTPException(status_code=403, detail="Contexto comercial inválido")
        if account_type == "COMMERCIAL" and (
            not payload.get("tenant_id") or "saas" not in scopes
        ):
            raise HTTPException(status_code=403, detail="Contexto comercial inválido")
        if account_type == "PLATFORM_ADMIN" and "backoffice" not in scopes:
            raise HTTPException(status_code=403, detail="Escopo administrativo inválido")
    return payload


async def _validate_token_session(token: str, session: AsyncSession) -> dict:
    payload = _decode_platform_token(token)
    try:
        authenticated_user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token inválido: identificador de usuário ausente.") from exc

    # The signed JWT establishes only the user identity. RLS can now scope the
    # session and membership bootstrap to that user before Tenant authorization.
    session.info["user_id"] = authenticated_user_id
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    cached = _cache_get(token_hash)

    if cached is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão encerrada ou revogada")

    # Sessões válidas precisam consultar expira_em em cada requisição; cachear
    # o resultado positivo permitiria ultrapassar o timeout configurado.
    if cached is not False:
        from core.models.sessao import SessaoAtiva
        try:
            result = await session.execute(
                select(SessaoAtiva.status, SessaoAtiva.expira_em).where(
                    SessaoAtiva.token_hash == token_hash
                )
            )
            sessao = result.one_or_none()
            sessao_status = sessao[0] if sessao else None

            if payload.get("impersonating") is True:
                impersonation_id = payload.get("impersonation_id")
                if impersonation_id:
                    from core.models.admin_impersonation import AdminImpersonation
                    imp_stmt = select(AdminImpersonation.fim).where(
                        AdminImpersonation.id == uuid.UUID(str(impersonation_id))
                    )
                    imp_res = await session.execute(imp_stmt)
                    imp_row = imp_res.one_or_none()
                    if imp_row is None or imp_row[0] is not None:
                        _cache_set(token_hash, False)
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Sessão de impersonação inexistente ou encerrada.",
                        )
                _cache_set(token_hash, True)
                return payload

            if payload.get("session_required") is True and sessao is None:
                _cache_set(token_hash, False)
                raise HTTPException(status_code=401, detail="Sessão inexistente ou revogada")

            if sessao_status is not None and sessao_status != "ATIVA":
                _cache_set(token_hash, False)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão encerrada ou revogada")

            expiracao = sessao[1] if sessao else None
            if expiracao is not None and expiracao.tzinfo is None:
                expiracao = expiracao.replace(tzinfo=timezone.utc)
            if expiracao is not None and expiracao <= datetime.now(timezone.utc):
                await session.execute(
                    update(SessaoAtiva).where(SessaoAtiva.token_hash == token_hash).values(status="EXPIRADA")
                )
                await session.commit()
                _cache_set(token_hash, False)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada por inatividade")

            _cache_set(token_hash, True)
        except (asyncio.TimeoutError, OSError, SQLAlchemyError) as exc:
            logger.error(
                "Falha ao validar sessão do usuário",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Banco de dados indisponível ou pool de conexões esgotado. Tente novamente em instantes.",
            ) from exc
        except Exception as exc:
            if _is_connection_exhaustion_error(exc):
                logger.warning(
                    "Pool de conexões do Postgres esgotado ao validar sessão",
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Banco de dados indisponível ou pool de conexões esgotado. Tente novamente em instantes.",
                ) from exc
            raise

    return payload


async def get_global_user_claims(
    token: str = Depends(get_token),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Valida identidade global, inclusive contas sem tenant."""
    return await _validate_token_session(token, session)


async def get_current_user_claims(
    request: Request = None,
    token: str = Depends(verify_commercial_jwt_guardrail),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Valida identidade/sessão e ativa claim Tenant somente após membership."""
    claims = await _validate_token_session(token, session)

    # Tratamento de Impersonação (Acesso Assistido por Administrador ou Suporte)
    if claims.get("impersonating") is True:
        # Se estiver em modo READ_ONLY, bloqueia qualquer mutação de dados (POST, PUT, PATCH, DELETE)
        if (
            claims.get("impersonation_mode") == "READ_ONLY"
            and request is not None
            and request.method.upper() in ("POST", "PUT", "PATCH", "DELETE")
        ):
            path = str(getattr(getattr(request, "url", None), "path", ""))
            # Rotas de controle da própria impersonação ou logout são liberadas
            if not path.startswith("/api/v1/backoffice/impersonate") and not path.endswith(("/auth/logout", "/auth/heartbeat")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Modo de suporte Somente Leitura ativo. Operações de gravação/edição estão bloqueadas para proteção dos dados do cliente. Alterne para o Modo Edição se necessário.",
                )

        tenant_id_str = claims.get("tenant_id")
        if tenant_id_str:
            try:
                tenant_id = uuid.UUID(str(tenant_id_str))
                await _activate_session_tenant(session, tenant_id)
            except Exception as exc:
                logger.error(f"Erro ao ativar contexto de tenant para impersonação: {exc}")
        return claims

    tenant_id_str = claims.get("tenant_id")
    if not tenant_id_str:
        return claims

    try:
        tenant_id = uuid.UUID(str(tenant_id_str))
        user_id = uuid.UUID(str(claims["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR) from exc

    if claims.get("is_superuser"):
        await _activate_session_tenant(session, tenant_id)
        return claims

    await _validate_and_apply_tenant_membership(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        claims=claims,
        request=request,
    )
    await _activate_session_tenant(session, tenant_id)
    return claims

async def get_tenant_id(
    request: Request,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
) -> uuid.UUID:
    """Recupera e garante que o usuário pertence ao Tenant que ele está tentando operar."""
    tenant_id_str = claims.get("tenant_id")
    header_tenant_id_str = request.headers.get("x-tenant-id")
    if tenant_id_str:
        tenant_id = uuid.UUID(tenant_id_str)
        if header_tenant_id_str:
            try:
                header_tenant_id = uuid.UUID(header_tenant_id_str)
            except ValueError:
                raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)
            if header_tenant_id != tenant_id:
                raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)
        if not claims.get("is_superuser") and not claims.get("impersonating") and "is_read_only" not in claims:
            try:
                user_id = uuid.UUID(claims["sub"])
            except (KeyError, ValueError):
                raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)
            await _validate_and_apply_tenant_membership(
                session=session,
                tenant_id=tenant_id,
                user_id=user_id,
                claims=claims,
                request=request,
            )
        await _activate_session_tenant(session, tenant_id)
        return tenant_id

    user_id_str = claims.get("sub")
    if not user_id_str:
        logger.warning("Tentativa de requisição sem tenant e sem sub no JWT.")
        raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=403, detail="Token inválido: identificador de usuário malformado.")

    from core.models.auth import TenantUsuario

    if header_tenant_id_str:
        try:
            header_tenant_id = uuid.UUID(header_tenant_id_str)
        except ValueError:
            raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

        await _validate_and_apply_tenant_membership(
            session=session,
            tenant_id=header_tenant_id,
            user_id=user_id,
            claims=claims,
            request=request,
        )
        await _activate_session_tenant(session, header_tenant_id)
        return header_tenant_id

    result = await session.execute(
        select(TenantUsuario.tenant_id).where(
            TenantUsuario.usuario_id == user_id,
            TenantUsuario.status == "ATIVO",
        ).distinct()
    )
    tenant_ids = list(result.scalars().all())

    if len(tenant_ids) == 1:
        resolved_tenant_id = tenant_ids[0]
        logger.warning(
            "JWT sem tenant_id resolvido pelo único tenant ativo do usuário.",
            user_id=str(user_id),
            tenant_id=str(resolved_tenant_id),
        )
        await _validate_and_apply_tenant_membership(
            session=session,
            tenant_id=resolved_tenant_id,
            user_id=user_id,
            claims=claims,
            request=request,
        )
        await _activate_session_tenant(session, resolved_tenant_id)
        return resolved_tenant_id

    if len(tenant_ids) > 1:
        raise HTTPException(
            status_code=403,
            detail=TENANT_CONTEXT_ERROR,
        )

    raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

async def get_user_id(
    claims: dict = Depends(get_current_user_claims)
) -> uuid.UUID | None:
    """Extrai o user_id (sub) do JWT para uso em audit logs."""
    sub = claims.get("sub")
    if sub:
        try:
            return uuid.UUID(sub)
        except (ValueError, AttributeError):
            pass
    return None

async def get_current_user(
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session)
):
    """Retorna o objeto Usuario completo do banco de dados."""
    from core.models.auth import Usuario
    user_id_str = claims.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: sem identificador de usuário.")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: ID de usuário malformado.")

    result = await session.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        if claims.get("impersonating") or claims.get("is_superuser"):
            from core.models.admin_user import AdminUser
            admin_res = await session.execute(select(AdminUser).where(AdminUser.id == user_id))
            admin = admin_res.scalar_one_or_none()
            if admin and admin.ativo:
                return admin
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo.")
    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo.")
    return user


async def get_current_user_identity(
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Validate the current user with a minimal projection for notification reads."""
    from types import SimpleNamespace
    from core.models.auth import Usuario

    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token inválido: identificador de usuário ausente.") from exc

    row = (await session.execute(
        select(Usuario.id, Usuario.ativo).where(Usuario.id == user_id)
    )).one_or_none()
    if row is None or not row.ativo:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo.")
    return SimpleNamespace(id=row.id, ativo=row.ativo)

async def get_current_tenant(
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session)
):
    """Retorna o objeto Tenant completo do banco."""
    from core.models.tenant import Tenant

    tenant_id_str = claims.get("tenant_id")
    tenant_id: uuid.UUID | None = None
    if tenant_id_str:
        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido: tenant ID malformado.")

    user_id: uuid.UUID | None = None
    if not claims.get("is_superuser") and not claims.get("impersonating"):
        user_id_str = claims.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TENANT_CONTEXT_ERROR)

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido: identificador de usuário malformado.")

        from core.models.auth import TenantUsuario
        if tenant_id is not None:
            membership = await session.execute(
                select(TenantUsuario.id).where(
                    TenantUsuario.tenant_id == tenant_id,
                    TenantUsuario.usuario_id == user_id,
                    TenantUsuario.status == "ATIVO",
                )
            )
            if membership.scalar_one_or_none() is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TENANT_CONTEXT_ERROR)

    if tenant_id is None:
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TENANT_CONTEXT_ERROR)

        from core.models.auth import TenantUsuario
        result = await session.execute(
            select(TenantUsuario.tenant_id).where(
                TenantUsuario.usuario_id == user_id,
                TenantUsuario.status == "ATIVO",
            ).distinct()
        )
        tenant_ids = list(result.scalars().all())

        if len(tenant_ids) == 1:
            tenant_id = tenant_ids[0]
            logger.warning(
                "JWT sem tenant_id resolvido pelo único tenant ativo do usuário.",
                user_id=str(user_id),
                tenant_id=str(tenant_id),
            )
        elif len(tenant_ids) > 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=TENANT_CONTEXT_ERROR,
            )
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TENANT_CONTEXT_ERROR)

    await _activate_session_tenant(session, tenant_id)
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não encontrado ou inativo.")
    return tenant

async def get_current_admin(claims: dict = Depends(get_current_user_claims)) -> dict:
    """Garante que o usuário é um operador do Backoffice administrativo do SaaS."""
    is_admin = (
        claims.get("is_superuser")
        or claims.get("backoffice_role") in ("super_admin", "admin", "suporte", "financeiro", "comercial")
        or (claims.get("role") in ("super_admin", "admin", "suporte", "financeiro", "comercial") and claims.get("product_scope") == "backoffice")
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao Backoffice administrativo."
        )
    return claims

# ==============================================================================
# SECURITY GATES (RBAC / Feature Flags)
# ==============================================================================

async def _resolve_grupo_id(
    request: Request,
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> uuid.UUID | None:
    """
    Compatibilidade temporária.

    O sistema não usa mais agrupamento por grupo. O tenant é a raiz de
    autorização e assinatura, então esta função existe apenas para não quebrar
    imports antigos.
    """
    return None


def _assinatura_ativa_filter():
    """
    Retorna a cláusula de status para assinaturas consideradas ativas.

    PENDENTE_PAGAMENTO é excluído intencionalmente: inadimplentes não passam nos
    feature gates. A carência (grace_period_days) é verificada separadamente pelo
    job de suspensão — não abre acesso a recursos durante a carência.
    """
    from core.models.billing import AssinaturaTenant
    from datetime import date, datetime, timezone
    return AssinaturaTenant.status.in_(["ATIVA", "TRIAL"])


async def _get_modulos_do_tenant(
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> list[str]:
    """Retorna módulos ativos das assinaturas do tenant."""
    from core.models.billing import AssinaturaTenant, PlanoAssinatura

    stmt = (
        select(PlanoAssinatura.modulos_inclusos)
        .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .where(
            AssinaturaTenant.tenant_id == tenant_id,
            _assinatura_ativa_filter(),
            AssinaturaTenant.tipo_assinatura == "TENANT",
        )
    )

    results = await session.execute(stmt)
    rows = results.scalars().all()

    # União de módulos de todas as assinaturas encontradas
    modulos: set[str] = set()
    for row in rows:
        if row:
            modulos.update(row)
    return list(modulos)


def require_module(required_module: str):
    """Feature Gate Dinâmico — valida se o tenant tem o módulo contratado."""
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_session)
    ):
        from core.constants import Modulos

        # SaaS admin tem acesso irrestrito a todos os módulos
        if claims.get("is_superuser"):
            return

        tenant_id_str = claims.get("tenant_id")
        request_path = str(getattr(getattr(request, "url", None), "path", "")) if request else ""
        request_method = getattr(request, "method", "")
        if not tenant_id_str:
            raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

        tenant_id = uuid.UUID(tenant_id_str)

        # Suporte técnico em impersonação usa a lista de módulos resolvida na emissão do token
        if claims.get("impersonating"):
            allowed_modules = claims.get("modules") or []
        else:
            allowed_modules = await _get_modulos_do_tenant(tenant_id, session)

            if Modulos.CORE not in allowed_modules:
                logger.error(f"CRITICAL: Tenant {tenant_id} sem módulo CORE")
                raise HTTPException(status_code=403, detail="Licença base inválida. Contate o suporte.")

        if required_module not in allowed_modules:
            from core.constants import ModuloMetadata
            modulo_info = ModuloMetadata.get_modulo_info(required_module)
            modulo_nome = modulo_info.get("nome", required_module)
            raise HTTPException(
                status_code=402,
                detail=f"Este recurso ({modulo_nome}) não está incluído no plano atual. Faça upgrade do plano para continuar.",
                headers={"X-Module-Required": required_module}
            )

        # Telemetria: incrementa contador diário de uso em background
        try:
            from core.services.module_usage_service import increment_module_usage
            from datetime import date
            await increment_module_usage(session, tenant_id, required_module, date.today())
            await session.commit()
            # O contexto RLS é transacional (SET LOCAL) e é removido pelo
            # commit acima. Reative-o antes de devolver o controle ao router;
            # caso contrário, a primeira operação de escrita do endpoint pode
            # ser rejeitada pela política de tenant.
            await _activate_session_tenant(session, tenant_id)
        except Exception:
            try:
                await session.rollback()
                await _activate_session_tenant(session, tenant_id)
            except Exception:
                pass  # Telemetria nunca deve bloquear a requisição

        return True
    return _dependency

def require_tier(minimum_tier: "PlanTier"):
    """Feature Gate de Tier — valida se o tenant tem o tier mínimo exigido."""
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_session)
    ):
        from core.models.billing import AssinaturaTenant, PlanoAssinatura
        from core.constants import PlanTier

        # SaaS admin e suporte técnico em impersonação têm acesso irrestrito
        if claims.get("is_superuser") or claims.get("impersonating"):
            return True

        tenant_id_str = claims.get("tenant_id")
        request_path = str(getattr(getattr(request, "url", None), "path", "")) if request else ""
        request_method = getattr(request, "method", "")
        if not tenant_id_str:
            raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

        tenant_id = uuid.UUID(tenant_id_str)
        tier_str = claims.get("plan_tier")

        if not tier_str:
            stmt = (
                select(PlanoAssinatura.plan_tier)
                .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
                .where(
                    AssinaturaTenant.tenant_id == tenant_id,
                    _assinatura_ativa_filter(),
                    AssinaturaTenant.tipo_assinatura == "TENANT",
                )
            )
            stmt = stmt.limit(1)
            result = await session.execute(stmt)
            tier_str = result.scalar_one_or_none()

        if not tier_str:
            logger.bind(
                event="monetization_blocked",
                surface="backend.require_tier",
                feature="tier_gate",
                tenant_id=str(tenant_id),
                required_tier=minimum_tier.value,
                current_tier=None,
                path=request_path,
                method=request_method,
                reason="missing_active_subscription",
            ).info("monetization_blocked")
            raise HTTPException(status_code=402, detail=PLAN_INACTIVE_ERROR)

        try:
            tenant_tier = PlanTier(tier_str)
        except ValueError:
            logger.bind(
                event="monetization_blocked",
                surface="backend.require_tier",
                feature="tier_gate",
                tenant_id=str(tenant_id),
                required_tier=minimum_tier.value,
                current_tier=tier_str,
                path=request_path,
                method=request_method,
                reason="invalid_tier_configuration",
            ).info("monetization_blocked")
            raise HTTPException(status_code=402, detail=PLAN_INVALID_ERROR)

        # Política All-In por tamanho de propriedade (limite_hectares / HEq):
        # todas as assinaturas ativas têm acesso completo às funcionalidades dos módulos contratados,
        # independentemente do tier legado (BASICO/PROFISSIONAL/ENTERPRISE).
        return tenant_tier
    return _dependency

def require_any_module(*required_modules: str):
    """Feature Gate que permite acesso se o tenant tiver QUALQUER UM dos módulos listados."""
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_session)
    ):
        tenant_id_str = claims.get("tenant_id")
        if not tenant_id_str:
            raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)
        tenant_id = uuid.UUID(tenant_id_str)
        allowed_modules = await _get_modulos_do_tenant(tenant_id, session)
        if not any(mod in allowed_modules for mod in required_modules):
            raise HTTPException(
                status_code=402,
                detail=f"Este recurso não está incluído no plano atual. Módulos necessários: {', '.join(required_modules)}. Faça upgrade do plano para continuar.",
            )
        return True
    return _dependency

def require_all_modules(*required_modules: str):
    """Feature Gate que permite acesso APENAS se o tenant tiver TODOS os módulos listados."""
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_session)
    ):
        tenant_id_str = claims.get("tenant_id")
        if not tenant_id_str:
            raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)
        tenant_id = uuid.UUID(tenant_id_str)
        allowed_modules = await _get_modulos_do_tenant(tenant_id, session)
        missing = [mod for mod in required_modules if mod not in allowed_modules]
        if missing:
            raise HTTPException(
                status_code=402,
                detail=f"Este recurso requer os módulos: {', '.join(missing)}. Faça upgrade do plano para continuar.",
            )
        return True
    return _dependency

def get_grupos_auth(claims: dict) -> list[str]:
    """Extrai a lista de grupo UUIDs autorizados do JWT."""
    return claims.get("grupos_auth", [])


def require_grupo_access():
    """
    Compatibilidade para endpoints que ainda enviam x-fazenda-id.

    O modelo atual não usa grupo. Então validamos apenas se o usuário é owner
    do tenant ou possui vínculo explícito à fazenda informada.
    """
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_session)
    ):
        from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
        from core.models.auth import TenantUsuario

        # is_owner or impersonating bypasses group check
        if claims.get("impersonating"):
            return True
        tenant_id_str = claims.get("tenant_id")
        user_id_str = claims.get("sub")
        if not tenant_id_str or not user_id_str:
            raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

        tenant_id = uuid.UUID(tenant_id_str)
        user_id = uuid.UUID(user_id_str)

        tu_stmt = select(TenantUsuario).where(
            TenantUsuario.tenant_id == tenant_id,
            TenantUsuario.usuario_id == user_id,
            TenantUsuario.status == "ATIVO"
        )
        tu = (await session.execute(tu_stmt)).scalar_one_or_none()
        if tu and tu.is_owner:
            return True

        fazenda_id_header = request.headers.get("x-fazenda-id")
        if not fazenda_id_header:
            return True  # No fazenda context — skip group check

        try:
            unidade_produtiva_id = uuid.UUID(fazenda_id_header)
        except ValueError:
            raise HTTPException(status_code=400, detail="x-fazenda-id inválido")

        fazenda_stmt = select(Fazenda).where(
            Fazenda.id == unidade_produtiva_id,
            Fazenda.tenant_id == tenant_id
        )
        fazenda = (await session.execute(fazenda_stmt)).scalar_one_or_none()
        if not fazenda:
            raise HTTPException(status_code=404, detail="Fazenda não encontrada")

        from core.models.auth import FazendaUsuario
        fu_stmt = select(FazendaUsuario).where(
            FazendaUsuario.tenant_id == tenant_id,
            FazendaUsuario.usuario_id == user_id,
            FazendaUsuario.unidade_produtiva_id == unidade_produtiva_id
        )
        fu = (await session.execute(fu_stmt)).scalar_one_or_none()
        if not fu:
            from loguru import logger
            logger.warning(
                f"TenantViolationError: user {user_id} tentou acessar fazenda {unidade_produtiva_id} sem autorização"
            )
            raise HTTPException(status_code=403, detail="Acesso negado: você não tem acesso a esta fazenda")
        return True
    return _dependency


def require_role(roles_allowed: List[str]):
    from core.constants import normalize_tenant_role
    normalized_roles_allowed = [normalize_tenant_role(item) for item in roles_allowed]

    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims)
    ):
        from loguru import logger
        target_fazenda_id = request.headers.get("x-fazenda-id")
        fazendas_auth = claims.get("fazendas_auth", [])
        role = next((f.get("role") for f in fazendas_auth if f.get("id") == target_fazenda_id), None)

        # Admin/Owner do tenant tem acesso implícito a todas as fazendas
        tenant_role = claims.get("role")
        is_superuser = claims.get("is_superuser", False)
        role = normalize_tenant_role(role)
        tenant_role = normalize_tenant_role(tenant_role)
        logger.debug(f"require_role: fazenda={target_fazenda_id}, role_from_db={role}, tenant_role={tenant_role}, is_superuser={is_superuser}")

        # Owner e admin do tenant são tratados como 'admin' para permissão
        if is_superuser or tenant_role in ("owner", "admin"):
            role = "admin"

        if not role or role not in normalized_roles_allowed:
            raise HTTPException(status_code=403, detail="Role insuficiente nesta Fazenda de trabalho")
        return claims
    return _dependency

def require_permission(permissao: str):
    """Dependency para verificar permissão específica do admin do backoffice."""
    async def dependency(
        claims: dict = Depends(get_current_admin),
        session: AsyncSession = Depends(get_session)
    ):
        from core.constants import BackofficePermissions
        from core.models.admin_user import AdminUser
        if claims.get("is_superuser"):
            return claims
        claims_perms = claims.get("permissoes") or []
        if permissao in claims_perms:
            return claims
        user_id_str = claims.get("sub")
        if user_id_str:
            try:
                admin_id = uuid.UUID(user_id_str)
                result = await session.execute(
                    select(AdminUser).where(AdminUser.id == admin_id, AdminUser.ativo == True)
                )
                admin_user = result.scalar_one_or_none()
                if admin_user and (admin_user.tem_permissao(permissao) or BackofficePermissions.has_permission(admin_user.role, permissao)):
                    return claims
            except ValueError:
                pass
        role = claims.get("role", "admin")
        if BackofficePermissions.has_permission(role, permissao):
            return claims
        raise HTTPException(status_code=403, detail=f"Permissão negada: {permissao}")
    return dependency


def require_any_permission(*permissoes: Any):
    """Dependency para verificar se o operador possui pelo menos uma das permissões indicadas."""
    flat_perms: list[str] = []
    for item in permissoes:
        if isinstance(item, (list, tuple, set)):
            flat_perms.extend([str(x) for x in item])
        else:
            flat_perms.append(str(item))

    async def dependency(
        claims: dict = Depends(get_current_admin),
        session: AsyncSession = Depends(get_session)
    ):
        from core.constants import BackofficePermissions
        from core.models.admin_user import AdminUser
        if claims.get("is_superuser"):
            return claims
        claims_perms = claims.get("permissoes") or []
        for p in flat_perms:
            if p in claims_perms:
                return claims
        user_id_str = claims.get("sub")
        if user_id_str:
            try:
                admin_id = uuid.UUID(user_id_str)
                result = await session.execute(
                    select(AdminUser).where(AdminUser.id == admin_id, AdminUser.ativo == True)
                )
                admin_user = result.scalar_one_or_none()
                if admin_user:
                    for p in flat_perms:
                        if admin_user.tem_permissao(p) or BackofficePermissions.has_permission(admin_user.role, p):
                            return claims
            except ValueError:
                pass
        role = claims.get("role", "admin")
        for p in flat_perms:
            if BackofficePermissions.has_permission(role, p):
                return claims
        raise HTTPException(
            status_code=403,
            detail=f"Permissão negada. Requer ao menos uma das seguintes permissões: {', '.join(flat_perms)}"
        )
    return dependency

async def resolver_permissao_usuario(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    permission: str,
    fazenda_id: uuid.UUID | None = None,
) -> bool:
    """Checa se um usuário tem uma permissão de tenant, fora do fluxo de Depends do FastAPI.

    Mesma lógica de `require_tenant_permission`, extraída para reuso em contextos
    que não são request handlers (ex: filtrar ações visíveis numa listagem).
    Não levanta exceção — retorna bool.
    """
    from core.constants import TenantPermissions
    from core.models.auth import TenantUsuario, PerfilAcesso, FazendaUsuario

    stmt = (
        select(TenantUsuario, PerfilAcesso)
        .outerjoin(PerfilAcesso, TenantUsuario.perfil_id == PerfilAcesso.id)
        .where(TenantUsuario.tenant_id == tenant_id, TenantUsuario.usuario_id == usuario_id, TenantUsuario.status == "ATIVO")
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return False
    tenant_usuario, perfil_acesso = row
    if tenant_usuario.is_owner:
        return True
    if fazenda_id:
        stmt_f = (
            select(FazendaUsuario, PerfilAcesso)
            .outerjoin(PerfilAcesso, FazendaUsuario.perfil_fazenda_id == PerfilAcesso.id)
            .where(FazendaUsuario.tenant_id == tenant_id, FazendaUsuario.usuario_id == usuario_id, FazendaUsuario.unidade_produtiva_id == fazenda_id)
        )
        res_f = await session.execute(stmt_f)
        row_f = res_f.first()
        if row_f and row_f[1]:
            perfil_acesso = row_f[1]
    if perfil_acesso:
        return TenantPermissions.has_permission(
            perfil_acesso.nome, permission, perfil_acesso.permissoes
        )
    return False


async def resolver_role_tenant_usuario(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> str | None:
    """Retorna o identificador canônico do perfil do usuário no tenant.

    Mesma resolução usada por `require_role` no login (`auth_service.py`, onde
    `fazendas_auth[i].role` vem do perfil do TenantUsuario,
    não de `FazendaUsuario.perfil_fazenda_id` — ignorado ali também). `is_owner`
    é tratado como "admin", igual ao `require_role`. Retorna None se sem vínculo ativo.
    """
    from core.models.auth import TenantUsuario, PerfilAcesso

    stmt = (
        select(TenantUsuario, PerfilAcesso)
        .outerjoin(PerfilAcesso, TenantUsuario.perfil_id == PerfilAcesso.id)
        .where(TenantUsuario.tenant_id == tenant_id, TenantUsuario.usuario_id == usuario_id, TenantUsuario.status == "ATIVO")
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    tenant_usuario, perfil_acesso = row
    if tenant_usuario.is_owner:
        return "admin"
    if perfil_acesso:
        from core.constants import normalize_tenant_role
        return normalize_tenant_role(perfil_acesso.nome)
    return None


def require_tenant_permission(permission: str):
    """Dependency para verificar permissão específica no contexto do tenant."""
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        tenant_id: uuid.UUID = Depends(get_tenant_id),
        user: "Usuario" = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
    ):
        if claims.get("impersonating") or claims.get("role") == "owner" or claims.get("is_superuser"):
            return True
        fazenda_id = None
        fazenda_id_header = request.headers.get("x-fazenda-id")
        if fazenda_id_header:
            try:
                fazenda_id = uuid.UUID(fazenda_id_header)
            except ValueError:
                fazenda_id = None
        permitido = await resolver_permissao_usuario(session, tenant_id, user.id, permission, fazenda_id)
        if not permitido:
            raise HTTPException(status_code=403, detail=f"Permissão negada: {permission}")
        return True
    return _dependency


# ==============================================================================
# DECORATOR COMPOSTO — módulo + permissão em uma só chamada
# ==============================================================================

def require_module_and_permission(module: str, permission: str):
    """
    Decorator que combina require_module + require_tenant_permission em uma única
    dependência — impossível usar um sem o outro.

    Substitui o padrão propenso a erro:
        @require_module("AGRICOLA")
        @require_tenant_permission("agricola:safra:criar")

    Uso:
        @router.post("/")
        async def create(
            _=Depends(require_module_and_permission("AGRICOLA", "agricola:safra:criar")),
            ...
        ):
    """
    _mod_dep = require_module(module)
    _perm_dep = require_tenant_permission(permission)

    async def _combined(
        _mod=Depends(_mod_dep),
        _perm=Depends(_perm_dep),
    ):
        return True

    return _combined


# ==============================================================================
# LIMIT VALIDATION GATES
# ==============================================================================

def require_limit(limit_type: str):
    """
    Feature Gate de Limites — valida se o tenant não ultrapassou o limite contratado.

    Tipos de limite suportados:
    - "max_fazendas": Número máximo de fazendas no tenant
    - "max_usuarios": Número máximo de usuários simultâneos
    - "max_categorias_plano": Categorias customizáveis no plano de contas
    - "storage_limite_mb": Limite de armazenamento em MB

    Uso em router:
        @router.post("/", dependencies=[Depends(require_limit("max_fazendas"))])
    """
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_session)
    ):
        from core.models.billing import AssinaturaTenant, PlanoAssinatura
        from core.models.tenant import Tenant
        from sqlalchemy import func

        tenant_id_str = claims.get("tenant_id")
        if not tenant_id_str:
            raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

        tenant_id = uuid.UUID(tenant_id_str)

        # Buscar assinatura ativa do tenant
        stmt = (
            select(PlanoAssinatura, AssinaturaTenant)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                _assinatura_ativa_filter(),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            )
        )
        stmt = stmt.limit(1)
        result = await session.execute(stmt)
        row = result.first()
        plano = row[0] if row else None
        assinatura = row[1] if row else None

        if not plano:
            # Sem assinatura ativa — usar limites padrão ou bloquear
            logger.warning(f"Tenant {tenant_id} sem assinatura ativa para validação de limites")
            raise HTTPException(
                status_code=402,
                detail=PLAN_INACTIVE_ERROR,
            )

        # Validar limite conforme tipo
        if limit_type == "max_fazendas":
            limite = plano.max_fazendas
            if limite == -1:
                return True  # Ilimitado

            # Contar fazendas atuais do tenant
            from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
            count_stmt = select(func.count(Fazenda.id)).where(Fazenda.tenant_id == tenant_id, Fazenda.ativo == True)
            count_result = await session.execute(count_stmt)
            atual = count_result.scalar_one() or 0

            if atual >= limite:
                raise HTTPException(
                    status_code=402,
                    detail=_limit_message("fazendas", limite, atual, "fazenda(s) ativas"),
                    headers={"X-Limit-Type": "max_fazendas", "X-Limit-Max": str(limite), "X-Limit-Current": str(atual)},
                )

        elif limit_type == "limite_hectares":
            limite = float(plano.limite_hectares) if plano.limite_hectares is not None else None
            if limite is None or limite <= 0:
                return True  # Ilimitado

            from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
            area_stmt = select(
                func.coalesce(
                    func.sum(
                        func.coalesce(Fazenda.area_total_calculada_ha, Fazenda.area_total_ha, 0)
                    ),
                    0,
                )
            ).where(Fazenda.tenant_id == tenant_id, Fazenda.ativo == True)
            atual = float((await session.execute(area_stmt)).scalar_one() or 0)

            if atual >= limite:
                raise HTTPException(
                    status_code=402,
                    detail=_limit_message("hectares", limite, atual, "ha utilizados"),
                    headers={"X-Limit-Type": "limite_hectares", "X-Limit-Max": str(limite), "X-Limit-Current": str(atual)},
                )

        elif limit_type == "max_usuarios":
            # Valida limite de acessos simultâneos contratados
            limite = (
                (assinatura.usuarios_contratados if assinatura else None)
                or plano.limite_usuarios_maximo
                or plano.limite_usuarios_minimo
            )
            if limite is None:
                return True  # Ilimitado

            from core.models.sessao import SessaoAtiva
            from datetime import date, datetime, timezone
            agora = datetime.now(timezone.utc)
            count_stmt = select(func.count(SessaoAtiva.id)).where(
                SessaoAtiva.tenant_id == tenant_id,
                SessaoAtiva.status == "ATIVA",
                SessaoAtiva.expira_em > agora,
            )
            count_result = await session.execute(count_stmt)
            atual = count_result.scalar_one() or 0

            if atual >= limite:
                raise HTTPException(
                    status_code=402,
                    detail=_limit_message("acessos simultâneos", limite, atual, "acesso(s) simultâneo(s) em uso"),
                    headers={"X-Limit-Type": "max_usuarios", "X-Limit-Max": str(limite), "X-Limit-Current": str(atual)},
                )

        elif limit_type == "max_categorias_plano":
            limite = plano.max_categorias_plano
            if limite == -1:
                return True  # Ilimitado

            # Contar categorias do plano de contas
            from financeiro.models.plano_conta import PlanoConta
            count_stmt = select(func.count(PlanoConta.id)).where(
                PlanoConta.tenant_id == tenant_id,
                PlanoConta.ativo == True,
            )
            count_result = await session.execute(count_stmt)
            atual = count_result.scalar_one() or 0

            if atual >= limite:
                raise HTTPException(
                    status_code=402,
                    detail=_limit_message("categorias", limite, atual, "categoria(s)"),
                    headers={"X-Limit-Type": "max_categorias_plano", "X-Limit-Max": str(limite), "X-Limit-Current": str(atual)},
                )

        elif limit_type == "storage_limite_mb":
            # Buscar tenant para verificar storage
            tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
            tenant_result = await session.execute(tenant_stmt)
            tenant = tenant_result.scalar_one()

            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant não encontrado")

            limite = tenant.storage_limite_mb
            atual = tenant.storage_usado_mb

            if atual >= limite:
                raise HTTPException(
                    status_code=402,
                    detail=_limit_message("armazenamento", limite, atual, f"({atual}/{limite} MB)"),
                    headers={"X-Limit-Type": "storage_limite_mb", "X-Limit-Max": str(limite), "X-Limit-Current": str(atual)},
                )

        else:
            logger.error(f"Tipo de limite desconhecido: {limit_type}")
            raise HTTPException(status_code=500, detail="Tipo de limite não configurado")

        return True
    return _dependency


def check_limit_soft(limit_type: str) -> dict:
    """
    Verificação suave de limite — retorna status sem bloquear.

    Retorna: {"atual": int, "limite": int | None, "porcentagem": float, "atingido": bool}
    """
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_session)
    ):
        from core.models.billing import AssinaturaTenant, PlanoAssinatura
        from core.models.tenant import Tenant
        from sqlalchemy import func

        tenant_id_str = claims.get("tenant_id")
        if not tenant_id_str:
            return {"atual": 0, "limite": 0, "porcentagem": 0.0, "atingido": False}

        tenant_id = uuid.UUID(tenant_id_str)

        # Buscar assinatura ativa do tenant
        stmt = (
            select(PlanoAssinatura, AssinaturaTenant)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                _assinatura_ativa_filter(),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            )
        )
        stmt = stmt.limit(1)
        result = await session.execute(stmt)
        row = result.first()
        plano = row[0] if row else None
        assinatura = row[1] if row else None

        if not plano:
            return {"atual": 0, "limite": 0, "porcentagem": 0.0, "atingido": False}

        atual = 0
        limite = None

        if limit_type == "max_fazendas":
            limite = plano.max_fazendas
            if limite == -1:
                return {"atual": 0, "limite": None, "porcentagem": 0.0, "atingido": False}

            from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
            count_stmt = select(func.count(Fazenda.id)).where(Fazenda.tenant_id == tenant_id, Fazenda.ativo == True)
            count_result = await session.execute(count_stmt)
            atual = count_result.scalar_one() or 0

        elif limit_type == "limite_hectares":
            limite = float(plano.limite_hectares) if plano.limite_hectares is not None else None
            if limite is None or limite <= 0:
                return {"atual": 0, "limite": None, "porcentagem": 0.0, "atingido": False}

            from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
            area_stmt = select(
                func.coalesce(
                    func.sum(
                        func.coalesce(Fazenda.area_total_calculada_ha, Fazenda.area_total_ha, 0)
                    ),
                    0,
                )
            ).where(Fazenda.tenant_id == tenant_id, Fazenda.ativo == True)
            atual = float((await session.execute(area_stmt)).scalar_one() or 0)

        elif limit_type == "max_usuarios":
            limite = (
                (assinatura.usuarios_contratados if assinatura else None)
                or plano.limite_usuarios_maximo
                or plano.limite_usuarios_minimo
            )
            if limite is None:
                return {"atual": 0, "limite": None, "porcentagem": 0.0, "atingido": False}

            from core.models.sessao import SessaoAtiva
            from datetime import date, datetime, timezone
            agora = datetime.now(timezone.utc)
            count_stmt = select(func.count(SessaoAtiva.id)).where(
                SessaoAtiva.tenant_id == tenant_id,
                SessaoAtiva.status == "ATIVA",
                SessaoAtiva.expira_em > agora,
            )
            count_result = await session.execute(count_stmt)
            atual = count_result.scalar_one() or 0

        elif limit_type == "storage_limite_mb":
            tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
            tenant_result = await session.execute(tenant_stmt)
            tenant = tenant_result.scalar_one()

            if tenant:
                limite = tenant.storage_limite_mb
                atual = tenant.storage_usado_mb

        porcentagem = (atual / limite * 100) if limite and limite > 0 else 0.0
        atingido = atual >= limite if limite else False

        return {
            "atual": atual,
            "limite": limite,
            "porcentagem": round(porcentagem, 2),
            "atingido": atingido,
        }


# ==============================================================================
# ACESSO EXPLÍCITO POR FAZENDA (BL-03)
# ==============================================================================

def require_fazenda_access(fazenda_id_param: str = "unidade_produtiva_id"):
    """
    Dependency que verifica se o usuário tem acesso explícito à fazenda.

    Regras:
    - is_owner (TenantUsuario) → acesso irrestrito
    - FazendaUsuario existe com vigencia_fim NULL ou >= hoje → acesso permitido
    - Caso contrário → 403

    Uso:
        @router.get("/{unidade_produtiva_id}/dados")
        async def endpoint(
            unidade_produtiva_id: uuid.UUID,
            _: bool = Depends(require_fazenda_access("unidade_produtiva_id")),
            ...
        )
    """
    async def _dependency(
        request: Request,
        claims: dict = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_session),
    ) -> bool:
        from core.models.auth import TenantUsuario, FazendaUsuario
        from datetime import date as date_type

        tenant_id_str = claims.get("tenant_id")
        user_id_str = claims.get("sub")
        if not tenant_id_str or not user_id_str:
            raise HTTPException(status_code=403, detail=TENANT_CONTEXT_ERROR)

        tenant_id = uuid.UUID(tenant_id_str)
        user_id = uuid.UUID(user_id_str)

        # Resolve unidade_produtiva_id do path param ou header
        fazenda_id_value = request.path_params.get(fazenda_id_param) or request.headers.get("x-fazenda-id")
        if not fazenda_id_value:
            return True  # Sem contexto de fazenda — deixa passar (outro gate cuida)

        try:
            unidade_produtiva_id = uuid.UUID(str(fazenda_id_value))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Parâmetro '{fazenda_id_param}' inválido")

        # is_owner → acesso total
        tu_result = await session.execute(
            select(TenantUsuario).where(
                TenantUsuario.tenant_id == tenant_id,
                TenantUsuario.usuario_id == user_id,
                TenantUsuario.status == "ATIVO",
                TenantUsuario.is_owner == True,
            )
        )
        if tu_result.scalar_one_or_none():
            return True

        # Verificar FazendaUsuario com vigência válida
        hoje = date_type.today()
        fu_result = await session.execute(
            select(FazendaUsuario).where(
                FazendaUsuario.tenant_id == tenant_id,
                FazendaUsuario.usuario_id == user_id,
                FazendaUsuario.unidade_produtiva_id == unidade_produtiva_id,
            )
        )
        fu = fu_result.scalar_one_or_none()

        if not fu:
            logger.warning(
                f"require_fazenda_access: user {user_id} tentou acessar fazenda {unidade_produtiva_id} "
                f"sem FazendaUsuario. tenant={tenant_id}"
            )
            raise HTTPException(status_code=403, detail="Acesso negado: sem permissão para esta propriedade")

        # Verificar vigência em runtime (não depende do JWT)
        if fu.vigencia_fim and fu.vigencia_fim < hoje:
            logger.warning(
                f"require_fazenda_access: acesso expirado — user {user_id} fazenda {unidade_produtiva_id} "
                f"vigencia_fim={fu.vigencia_fim}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Acesso expirado em {fu.vigencia_fim.strftime('%d/%m/%Y')}. "
                       "Contate o gestor da assinatura para renovar."
            )

        if fu.vigencia_inicio and fu.vigencia_inicio > hoje:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso liberado apenas a partir de {fu.vigencia_inicio.strftime('%d/%m/%Y')}."
            )

        return True
    return _dependency


async def get_unidade_produtiva_context(
    request: Request,
    unidade_produtiva_id: uuid.UUID | None = Query(None),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Dependency padronizada para contexto operacional de fazenda/UP."""
    from core.models.auth import TenantUsuario
    from core.operational_context import resolve_unidade_produtiva_context

    user_id = None
    sub = claims.get("sub")
    if sub:
        try:
            user_id = uuid.UUID(sub)
        except ValueError:
            raise HTTPException(status_code=401, detail="Token inválido: usuário malformado.")

    # Superuser, suporte em impersonação e owner têm acesso amplo a todas as UPs do tenant
    if claims.get("is_superuser") or claims.get("impersonating") or claims.get("role") == "owner":
        user_id = None
    elif user_id is not None:
        owner = (
            await session.execute(
                select(TenantUsuario.id).where(
                    TenantUsuario.tenant_id == tenant_id,
                    TenantUsuario.usuario_id == user_id,
                    TenantUsuario.status == "ATIVO",
                    TenantUsuario.is_owner == True,
                )
            )
        ).scalar_one_or_none()
        if owner:
            user_id = None

    return await resolve_unidade_produtiva_context(
        session,
        tenant_id=tenant_id,
        request=request,
        unidade_produtiva_id=unidade_produtiva_id,
        user_id=user_id,
        required=False,
    )
