"""Rotas administrativas do Backoffice para gestão dinâmica de provedores climáticos.

Permite consultar situação operacional, alternar provedores (hot-swap), gerenciar credenciais
criptografadas, testar conectividade e acionar planos de contingência.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

UTC = timezone.utc
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import (
    get_session,
    require_any_permission,
    require_permission,
)
from core.schemas.agro_config_schemas import (
    KEY_CLIMA,
    AgroClimaConfig,
    PlatformWeatherCredentialItem,
    PlatformWeatherCredentialUpdateRequest,
    ProviderConnectivityTestRequest,
    ProviderConnectivityTestResponse,
    ProviderMetricsResponse,
    ProviderOperationalStatusItem,
    ProviderOperationalStatusResponse,
)
from core.services.admin_audit_service import AdminAuditService, resolve_admin_identity
from core.services.agro_config_service import agro_config_service
from core.services.platform_weather_credentials import PlatformWeatherCredentialsService
from public_clima.adapters import (
    verify_provider_public_authorization,
)
from public_clima.cache import ClimaCache
from public_clima.router import get_weather_orchestrator

router = APIRouter(prefix="/backoffice/agro/provedores", tags=["Backoffice - Provedores Climáticos"])


class ContingencyToggleRequest(BaseModel):
    """Solicitação de acionamento ou desativação de contingência operacional."""

    enable_contingency: bool
    target_provider: str | None = None
    motivo: str = Field(min_length=3, max_length=255, default="Acionamento operacional manual")


@router.get(
    "",
    response_model=ProviderOperationalStatusResponse,
    summary="Consulta a situação operacional consolidada dos provedores climáticos",
)
async def get_providers_status(
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:config:view")),
    session: AsyncSession = Depends(get_session),
) -> ProviderOperationalStatusResponse:
    """Retorna o provedor ativo, a cadeia de fallback e a situação de cada adaptador."""
    # 1. Carrega configuração do AgroClima
    valor, meta, ativo = await agro_config_service.get_config(session, KEY_CLIMA)
    cfg = AgroClimaConfig.model_validate(valor)

    # 2. Carrega credenciais mascaradas
    creds_resp = await PlatformWeatherCredentialsService.get_credentials_status(session)
    creds_map = {item.provider_slug.upper(): item for item in creds_resp.items}

    # 3. Carrega métricas do ClimaCache
    cache = ClimaCache(redis_url=settings.redis_url)
    shared = await cache.redis_ready()

    providers_list: list[ProviderOperationalStatusItem] = []

    # Provedores conhecidos
    defs = [
        ("WEATHERAPI", "WeatherAPI (Global)", True),
        ("OPENWEATHER", "OpenWeather One Call 3.0", True),
        ("OPEN_METEO", "Open-Meteo Forecast", False),
    ]

    for p_slug, p_name, req_cred in defs:
        cred = creds_map.get(p_slug)
        has_cred = bool(cred and cred.is_configured)
        masked_cred = cred.key_preview if cred else None

        is_active = cfg.active_provider.upper() == p_slug
        is_in_fallback = p_slug in [f.upper() for f in cfg.fallback_chain]
        order = (
            cfg.fallback_chain.index(p_slug) + 1
            if p_slug in cfg.fallback_chain
            else (
                cfg.fallback_chain.index(p_slug.lower()) + 1
                if p_slug.lower() in cfg.fallback_chain
                else None
            )
        )

        is_licensed = True
        if p_slug == "OPEN_METEO":
            is_licensed = bool(cfg.open_meteo_licensed or settings.open_meteo_allow_unlicensed_public)
        elif p_slug == "OPENWEATHER":
            is_licensed = bool(cfg.openweather_licensed or settings.openweather_allow_unlicensed_public or has_cred)

        # Status operacional
        status_op = "OPERACIONAL"
        if req_cred and not has_cred:
            status_op = "SEM_CREDENCIAL"
        elif not is_licensed:
            status_op = "NAO_LICENCIADO"

        # Métricas de consumo
        metrics = await cache.get_metrics(p_slug, shared)
        monthly_calls = metrics.get("upstream_calls_month", 0)
        p_limit = cfg.monthly_quota_limit if is_active else 0
        usage_pct = round((monthly_calls / float(p_limit)) * 100, 1) if p_limit > 0 else 0.0

        if p_limit > 0 and monthly_calls >= p_limit:
            status_op = "COTA_EXCEDIDA"

        last_err = None
        if metrics.get("timeouts", 0) > 0:
            last_err = f"{metrics['timeouts']} timeout(s) no mês"
        elif metrics.get("failures", 0) > 0:
            last_err = f"{metrics['failures']} falha(s) de upstream no mês"

        providers_list.append(
            ProviderOperationalStatusItem(
                slug=p_slug,
                nome=p_name,
                is_active=is_active,
                is_fallback=is_in_fallback,
                fallback_priority=order,
                status=status_op,
                has_credentials=has_cred,
                requires_credentials=req_cred,
                is_licensed=is_licensed,
                monthly_quota_limit=p_limit,
                monthly_calls=monthly_calls,
                quota_percentage=usage_pct,
                key_preview=masked_cred,
                last_error=last_err,
                last_tested_at=cred.last_updated if cred else None,
            )
        )

    calls_total = sum(p.monthly_calls for p in providers_list)
    quota_limit = cfg.monthly_quota_limit
    usage_total_pct = round((calls_total / float(quota_limit)) * 100, 1) if quota_limit > 0 else 0.0

    return ProviderOperationalStatusResponse(
        active_provider=cfg.active_provider.upper(),
        contingency_mode=cfg.force_contingency_mode,
        contingency_provider=cfg.contingency_provider,
        providers=providers_list,
        fallback_chain=[f.upper() for f in cfg.fallback_chain],
        timeout_seconds=cfg.timeout_seconds,
        cache_ttl_seconds=cfg.cache_ttl_seconds,
        monthly_quota_limit=quota_limit,
        current_month_calls=calls_total,
        quota_percentage=usage_total_pct,
        revision=meta.revision if meta else 1,
    )


_connectivity_test_ratelimit: dict[str, list[float]] = {}


def _check_local_rate_limit(key: str, max_calls: int = 10, window_secs: int = 60) -> bool:
    """Valida rate limit local quando Redis estiver indisponível ou em testes."""
    now = time.time()
    calls = _connectivity_test_ratelimit.setdefault(key, [])
    _connectivity_test_ratelimit[key] = [t for t in calls if now - t < window_secs]
    if len(_connectivity_test_ratelimit[key]) >= max_calls:
        return False
    _connectivity_test_ratelimit[key].append(now)
    return True


@router.put(
    "/config",
    summary="Atualiza a política de provedores climáticos, timeouts e fallback",
)
async def update_providers_config(
    body: AgroClimaConfig,
    expected_revision: int | None = Query(None, description="Versão esperada para concorrência otimista"),
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:config:edit")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Valida e aplica a nova configuração climática sem exigir restart de serviço."""
    active_slug = body.active_provider.upper()

    # 1. Carrega mapa de credenciais existentes para validação rigorosa de licenciamento
    creds_resp = await PlatformWeatherCredentialsService.get_credentials_status(session)
    creds_map = {item.provider_slug.upper(): item.is_configured for item in creds_resp.items}

    # 2. Valida autorização pública de active_provider
    authorized, reason = verify_provider_public_authorization(active_slug, body, creds_map)
    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Provedor ativo '{active_slug}' não autorizado para uso público: {reason}",
        )

    # 3. Valida provedores na cadeia de fallback (registra alerta se não licenciado; orquestrador ignora em runtime)
    for fb in body.fallback_chain:
        fb_auth, fb_reason = verify_provider_public_authorization(fb, body, creds_map)
        if not fb_auth:
            logger.warning(
                "Provedor na cadeia de fallback não possui licença pública e será ignorado em runtime",
                provider=fb,
                reason=fb_reason,
            )

    # 4. Valida provedor de contingência se configurado
    if body.contingency_provider:
        cp_auth, cp_reason = verify_provider_public_authorization(body.contingency_provider, body, creds_map)
        if not cp_auth:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Provedor de contingência '{body.contingency_provider}' não autorizado para uso público: {cp_reason}",
            )

    # Persiste via agro_config_service
    record, new_meta = await agro_config_service.update_config(
        session=session,
        chave=KEY_CLIMA,
        novo_valor=body.model_dump(),
        admin_claims=admin_claims,
        descricao="Atualização da política de provedores climáticos e contingência",
        expected_revision=expected_revision,
    )

    # Invalida cache em memória do orquestrador
    orchestrator = get_weather_orchestrator()
    orchestrator.invalidate_cache()

    return {
        "status": "success",
        "chave": KEY_CLIMA,
        "valor": record.valor,
        "metadata": new_meta.model_dump(),
        "descricao": record.descricao,
        "ativo": record.ativo,
    }


@router.post(
    "/credentials",
    response_model=PlatformWeatherCredentialItem,
    summary="Armazena ou rotaciona credencial criptografada de um provedor",
)
async def save_provider_credential(
    body: PlatformWeatherCredentialUpdateRequest,
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:credentials:manage")),
    session: AsyncSession = Depends(get_session),
) -> PlatformWeatherCredentialItem:
    """Criptografa com AES-256-GCM e armazena em repouso no cofre de credenciais da plataforma."""
    item = await PlatformWeatherCredentialsService.save_credential(
        session=session,
        admin_claims=admin_claims,
        provider_slug=body.provider_slug,
        api_key=body.api_key,
        key_version=body.key_version,
        force_on_upstream_incident=body.force_on_upstream_incident,
        incident_justification=body.incident_justification,
    )

    orchestrator = get_weather_orchestrator()
    orchestrator.invalidate_cache()

    return item


@router.post(
    "/credentials/reencrypt",
    summary="Migração criptográfica atômica: reencripta todas as credenciais para o KEK mais recente (v2)",
)
async def reencrypt_provider_credentials(
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:credentials:manage")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Rotaciona todas as credenciais registradas para o KEK v2 isolado."""
    result = await PlatformWeatherCredentialsService.reencrypt_all_credentials(session, admin_claims)
    orchestrator = get_weather_orchestrator()
    orchestrator.invalidate_cache()
    return result


@router.post(
    "/test-connection",
    response_model=ProviderConnectivityTestResponse,
    summary="Testa conectividade e latência com um provedor meteorológico",
)
async def test_provider_connection(
    body: ProviderConnectivityTestRequest,
    admin_claims: dict[str, Any] = Depends(
        require_any_permission("backoffice:agro:connectivity:test", "backoffice:agro:credentials:manage")
    ),
    session: AsyncSession = Depends(get_session),
) -> ProviderConnectivityTestResponse:
    """Executa requisição leve de teste com o provedor com proteção de rate limit e sem expor segredos."""
    admin_id = str(admin_claims.get("sub") or "global_admin")
    rate_key = f"rate:connectivity_test:{admin_id}"

    # Rate limiting: max 10 chamadas por minuto
    cache = ClimaCache(redis_url=settings.redis_url)
    shared = await cache.redis_ready()

    if shared:
        try:
            r = await cache._get_redis()
            current = await r.incr(rate_key)
            if current == 1:
                await r.expire(rate_key, 60)
            if current > 10:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Limite de taxa excedido para testes de conectividade (máximo 10 requisições por minuto).",
                )
        except HTTPException:
            raise
        except Exception:
            if not _check_local_rate_limit(rate_key, max_calls=10, window_secs=60):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Limite de taxa excedido para testes de conectividade (máximo 10 requisições por minuto).",
                )
    else:
        if not _check_local_rate_limit(rate_key, max_calls=10, window_secs=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Limite de taxa excedido para testes de conectividade (máximo 10 requisições por minuto).",
            )

    return await PlatformWeatherCredentialsService.test_connectivity(
        provider_slug=body.provider_slug,
        api_key_override=body.api_key_override,
        session=session,
    )


@router.post(
    "/contingency/toggle",
    summary="Aciona ou desativa manualmente a contingência de provedor climático",
)
async def toggle_contingency(
    body: ContingencyToggleRequest,
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:contingency:trigger")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Alterna imediatamente o provedor ativo para a contingência ou restaura a configuração primária."""
    valor, meta, ativo = await agro_config_service.get_config(session, KEY_CLIMA)
    cfg = AgroClimaConfig.model_validate(valor)

    admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)

    if body.enable_contingency:
        target = (body.target_provider or cfg.contingency_provider or "").upper()
        if not target:
            # Seleciona o primeiro provedor alternativo da cadeia
            for p in cfg.fallback_chain:
                if p.upper() != cfg.active_provider.upper():
                    target = p.upper()
                    break
        if not target:
            target = "OPEN_METEO"

        # Valida licenciamento e prontidão do provedor de destino antes de acionar contingência
        creds_resp = await PlatformWeatherCredentialsService.get_credentials_status(session)
        creds_map = {item.provider_slug.upper(): item.is_configured for item in creds_resp.items}
        authorized, reason = verify_provider_public_authorization(target, cfg, creds_map)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Provedor de contingência '{target}' não autorizado para uso público: {reason}",
            )

        dados_anteriores = cfg.model_dump()
        cfg.contingency_provider = cfg.active_provider  # Lembra o original para retorno
        cfg.active_provider = target

        await agro_config_service.update_config(
            session=session,
            chave=KEY_CLIMA,
            novo_valor=cfg.model_dump(),
            admin_claims=admin_claims,
            descricao=f"Contingência ativada: {cfg.active_provider} -> {target}. Motivo: {body.motivo}",
        )

        await AdminAuditService.log_action(
            session=session,
            admin_id=admin_uid,
            admin_email=admin_email,
            acao="agro.contingency.activate",
            entidade="configuracoes_saas",
            descricao=f"Contingência acionada para o provedor {target}.",
            dados_anteriores=dados_anteriores,
            dados_novos=cfg.model_dump(),
        )
    else:
        # Desativação de contingência
        restaurado = (cfg.contingency_provider or "WEATHERAPI").upper()

        creds_resp = await PlatformWeatherCredentialsService.get_credentials_status(session)
        creds_map = {item.provider_slug.upper(): item.is_configured for item in creds_resp.items}
        authorized, reason = verify_provider_public_authorization(restaurado, cfg, creds_map)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Não é possível restaurar o provedor '{restaurado}': {reason}",
            )

        dados_anteriores = cfg.model_dump()
        cfg.active_provider = restaurado
        cfg.contingency_provider = None

        await agro_config_service.update_config(
            session=session,
            chave=KEY_CLIMA,
            novo_valor=cfg.model_dump(),
            admin_claims=admin_claims,
            descricao=f"Contingência desativada. Provedor primário restaurado para {restaurado}.",
        )

        await AdminAuditService.log_action(
            session=session,
            admin_id=admin_uid,
            admin_email=admin_email,
            acao="agro.contingency.deactivate",
            entidade="configuracoes_saas",
            descricao=f"Contingência desativada. Provedor primário {restaurado} restaurado.",
            dados_anteriores=dados_anteriores,
            dados_novos=cfg.model_dump(),
        )

    orchestrator = get_weather_orchestrator()
    orchestrator.invalidate_cache()

    return {
        "status": "success",
        "contingency_active": body.enable_contingency,
        "active_provider": cfg.active_provider,
        "contingency_provider": cfg.contingency_provider,
    }


@router.get(
    "/metrics",
    response_model=ProviderMetricsResponse,
    summary="Métricas de consumo, cache e falhas por provedor",
)
async def get_providers_metrics(
    provider: str = Query("WEATHERAPI", description="Slug do provedor (ex: WEATHERAPI, OPENWEATHER, OPEN_METEO)"),
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:metrics:view")),
    session: AsyncSession = Depends(get_session),
) -> ProviderMetricsResponse:
    """Retorna métricas em tempo real extraídas do ClimaCache."""
    slug = provider.upper()
    cache = ClimaCache(redis_url=settings.redis_url)
    shared = await cache.redis_ready()

    valor, meta, ativo = await agro_config_service.get_config(session, KEY_CLIMA)
    cfg = AgroClimaConfig.model_validate(valor)

    metrics = await cache.get_metrics(slug, shared)
    upstream = metrics.get("upstream_calls_month", 0)
    limit = cfg.monthly_quota_limit if slug == cfg.active_provider.upper() else 0
    pct = round((upstream / float(limit)) * 100, 1) if limit > 0 else 0.0

    return ProviderMetricsResponse(
        provider_slug=slug,
        month=datetime.now(UTC).strftime("%Y-%m"),
        upstream_calls_month=upstream,
        monthly_quota_limit=limit,
        quota_usage_percent=pct,
        cache_hits=metrics.get("cache_hits", 0),
        cache_misses=metrics.get("cache_misses", 0),
        timeouts=metrics.get("timeouts", 0),
        failures=metrics.get("failures", 0),
        contingency_cache_used=0,
    )
