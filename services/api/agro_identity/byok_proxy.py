"""Camada de Proxy Delegado Seguro para Cotações Agropecuárias (BYOK).

Implementa:
1. Resolução segura de credenciais do usuário individual no cofre segregado.
2. Catálogo estrito de provedores e instrumentos agropecuários com bloqueio de SSRF.
3. Rate limiting dedicado por usuário e por provedor (Redis + fallback em memória).
4. Cache privado estritamente isolado por usuário (TTL = 60s, sem compartilhamento com cache público).
5. Controle de concorrência com semáforo e deduplicação single-flight por instrumento.
6. Separação rigorosa de contratos: Mercado FÍSICO nacional vs Mercado FUTURO internacional/B3.
7. Isolamento absoluto: não consome o pool de conexões do PostgreSQL comercial.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from loguru import logger
try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None  # type: ignore[assignment,misc]

from .byok_vault import ByokVaultService
from .config import (
    AGRO_BYOK_CACHE_TTL_SECONDS,
    AGRO_BYOK_CONCURRENCY_LIMIT,
    AGRO_BYOK_RATE_LIMIT_PER_MINUTE,
    AGRO_BYOK_REDIS_URL,
    AGRO_BYOK_REQUEST_TIMEOUT_SECONDS,
)
from .schemas import (
    ByokCotacaoResponse,
    ByokProviderInfo,
    ByokProviderStatus,
    SituacaoCotacao,
    TipoMercado,
)

# Catálogo oficial de provedores e status regulatório de licenciamento
BYOK_PROVIDERS_CATALOG: list[ByokProviderInfo] = [
    ByokProviderInfo(
        slug="SIMULATED",
        nome="Provedor Simulado Homologado",
        descricao="Ambiente sintético de homologação funcional sem custos e sem consumo de quota externa.",
        status=ByokProviderStatus.ATIVO,
        instrumentosSuportados=["SOJA", "MILHO", "BOI_GORDO", "CAFE", "TRIGO"],
        requerCredencial=True,
        avisoRegulatorio="Dados sintéticos calibrados para homologação funcional contínua (Fase C3).",
    ),
    ByokProviderInfo(
        slug="TWELVE_DATA",
        nome="Twelve Data Financial APIs",
        descricao="Provedor de mercado financeiro internacional com cotações de commodities via API REST/Websocket.",
        status=ByokProviderStatus.DESABILITADO_LICENCA,
        instrumentosSuportados=["SOJA", "MILHO", "TRIGO", "CAFE"],
        requerCredencial=True,
        avisoRegulatorio=(
            "Termos de Uso Twelve Data (Seção 4: Redistribution & Caching) proíbem expressamente o "
            "armazenamento em cache compartilhado e proxies multi-tenant em planos Basic/Developer. "
            "Acesso a cotações em tempo real da CBOT/CME exige licenciamento enterprise e taxas de bolsa."
        ),
    ),
    ByokProviderInfo(
        slug="POLYGON",
        nome="Polygon.io",
        descricao="Plataforma institucional de market data em tempo real.",
        status=ByokProviderStatus.DESABILITADO_LICENCA,
        instrumentosSuportados=["SOJA", "MILHO"],
        requerCredencial=True,
        avisoRegulatorio=(
            "Polygon.io não disponibiliza contratos futuros agrícolas CBOT em planos de varejo. "
            "Redistribuição delegada requer aditivo contratual específico com a CME Group."
        ),
    ),
    ByokProviderInfo(
        slug="IBKR",
        nome="Interactive Brokers Client Portal API",
        descricao="Acesso direto de corretagem e book de ofertas para clientes IBKR.",
        status=ByokProviderStatus.DESABILITADO_LICENCA,
        instrumentosSuportados=["SOJA", "MILHO", "BOI_GORDO", "CAFE", "TRIGO"],
        requerCredencial=True,
        avisoRegulatorio=(
            "Requer execução de Gateway local autenticado com 2FA ativo a cada 24 horas e "
            "assinatura de Market Data pessoal junto à CME/B3, inviabilizando delegação em nuvem stateless."
        ),
    ),
]

_COMMODITIES_PERMITIDAS = {"SOJA", "MILHO", "BOI_GORDO", "CAFE", "TRIGO"}
_PROVEDORES_PERMITIDOS = {"SIMULATED"}

# Expressões para validação e bloqueio absoluto de SSRF
_IP_OR_URL_PATTERN = re.compile(
    r"(?:https?://|ftp://|file://|gopher://|localhost|127\.\d+\.\d+\.\d+|169\.254\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+|::1|\[::\])",
    re.IGNORECASE,
)


def validar_ssrf_safety(parametro: str, nome_campo: str = "parâmetro") -> None:
    """Bloqueia preventivamente strings contendo URLs arbitrárias, IPs ou esquemas locais."""
    if _IP_OR_URL_PATTERN.search(parametro):
        logger.warning(
            f"Tentativa de SSRF ou injeção de URL detectada no campo '{nome_campo}': {parametro[:30]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valor inválido para o campo '{nome_campo}': URLs e endereços de rede são estritamente proibidos.",
        )


_SHARED_LOCAL_RATE_FALLBACK: dict[str, list[float]] = {}
_SHARED_LOCAL_CACHE_FALLBACK: dict[str, tuple[ByokCotacaoResponse, float]] = {}
_SHARED_FALLBACK_LOCK = asyncio.Lock()


def clear_local_byok_cache() -> None:
    """Limpa fallbacks em memória (usado para isolamento de testes e manutenção)."""
    _SHARED_LOCAL_RATE_FALLBACK.clear()
    _SHARED_LOCAL_CACHE_FALLBACK.clear()


class ByokRateLimiter:
    """Rate limiter por usuário e provedor utilizando Redis com fallback em memória."""

    def __init__(self, redis_client: Any, limit_per_minute: int = AGRO_BYOK_RATE_LIMIT_PER_MINUTE) -> None:
        self.redis = redis_client
        self.limit = limit_per_minute

    async def check_and_increment(self, user_id: uuid.UUID, provider_slug: str) -> None:
        """Verifica se o usuário excedeu a taxa permitida por minuto para o provedor."""
        key = f"agro:byok:ratelimit:{user_id}:{provider_slug}"
        now = time.monotonic()

        # 1. Tenta via Redis
        try:
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, 60)
            if current > self.limit:
                ttl = await self.redis.ttl(key)
                retry_after = max(1, ttl if ttl > 0 else 60)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Limite de requisições excedido para o provedor '{provider_slug}'. Máximo de {self.limit} req/min.",
                    headers={"Retry-After": str(retry_after)},
                )
            return
        except HTTPException:
            raise
        except Exception as exc:
            logger.debug(f"Redis indisponível para rate limiting BYOK ({exc}). Utilizando fallback em memória.")

        # 2. Fallback gracioso em memória compartilhado
        async with _SHARED_FALLBACK_LOCK:
            timestamps = _SHARED_LOCAL_RATE_FALLBACK.setdefault(key, [])
            cutoff = now - 60.0
            # Remove timestamps antigos
            timestamps = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self.limit:
                retry_after = int(max(1, 60.0 - (now - timestamps[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Limite de requisições excedido para o provedor '{provider_slug}' (memória). Máximo de {self.limit} req/min.",
                    headers={"Retry-After": str(retry_after)},
                )
            timestamps.append(now)
            _SHARED_LOCAL_RATE_FALLBACK[key] = timestamps


class ByokPrivateCache:
    """Cache privado de cotações estritamente isolado por usuário e por provedor."""

    def __init__(self, redis_client: Any, ttl_seconds: int = AGRO_BYOK_CACHE_TTL_SECONDS) -> None:
        self.redis = redis_client
        self.ttl = ttl_seconds

    def _build_key(self, user_id: uuid.UUID, provider_slug: str, commodity: str, tipo_mercado: TipoMercado) -> str:
        # Padrão estrito de chave garantindo isolamento total por usuário
        return f"agro:byok:quote:{user_id}:{provider_slug}:{commodity}:{tipo_mercado.value}"

    async def get(
        self,
        user_id: uuid.UUID,
        provider_slug: str,
        commodity: str,
        tipo_mercado: TipoMercado,
    ) -> ByokCotacaoResponse | None:
        key = self._build_key(user_id, provider_slug, commodity, tipo_mercado)

        # 1. Tenta via Redis
        try:
            raw = await self.redis.get(key)
            if raw:
                data = json.loads(raw)
                cotacao = ByokCotacaoResponse.model_validate(data)
                cotacao.cached = True
                return cotacao
        except Exception as exc:
            logger.debug(f"Redis get indisponível para cache BYOK ({exc}). Consultando fallback local.")

        # 2. Fallback em memória compartilhado
        async with _SHARED_FALLBACK_LOCK:
            entry = _SHARED_LOCAL_CACHE_FALLBACK.get(key)
            if entry:
                cotacao, expires_at = entry
                if expires_at > time.monotonic():
                    cotacao_copy = cotacao.model_copy()
                    cotacao_copy.cached = True
                    return cotacao_copy
                _SHARED_LOCAL_CACHE_FALLBACK.pop(key, None)

        return None

    async def set(
        self,
        user_id: uuid.UUID,
        provider_slug: str,
        commodity: str,
        tipo_mercado: TipoMercado,
        cotacao: ByokCotacaoResponse,
    ) -> None:
        key = self._build_key(user_id, provider_slug, commodity, tipo_mercado)
        payload = cotacao.model_dump(mode="json")

        # 1. Tenta gravar no Redis
        try:
            await self.redis.setex(key, self.ttl, json.dumps(payload))
        except Exception as exc:
            logger.debug(f"Redis setex indisponível para cache BYOK ({exc}). Gravando no fallback local.")

        # 2. Atualiza fallback em memória compartilhado
        async with _SHARED_FALLBACK_LOCK:
            _SHARED_LOCAL_CACHE_FALLBACK[key] = (cotacao, time.monotonic() + self.ttl)


class ByokProxyService:
    """Motor de Proxy Delegado Seguro para o ecossistema BYOK."""

    def __init__(
        self,
        vault_service: ByokVaultService,
        redis_url: str = AGRO_BYOK_REDIS_URL,
    ) -> None:
        self.vault = vault_service
        self.redis = None
        if Redis is not None and redis_url:
            try:
                self.redis = Redis.from_url(redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)
            except Exception:
                self.redis = None
        self.rate_limiter = ByokRateLimiter(self.redis)
        self.cache = ByokPrivateCache(self.redis)
        self.concurrency_semaphore = asyncio.Semaphore(AGRO_BYOK_CONCURRENCY_LIMIT)
        self.in_flight_locks: dict[str, asyncio.Lock] = {}
        self.in_flight_meta_lock = asyncio.Lock()

    async def close(self) -> None:
        """Libera recursos de conexão."""
        try:
            await self.redis.aclose()
        except Exception:
            pass

    def get_providers_catalog(self) -> list[ByokProviderInfo]:
        """Retorna o catálogo oficial de provedores homologados e respectivos avisos de licença."""
        return BYOK_PROVIDERS_CATALOG

    async def fetch_quote(
        self,
        usuario_id: uuid.UUID,
        commodity_raw: str,
        tipo_mercado: TipoMercado,
        provider_slug_raw: str = "SIMULATED",
    ) -> ByokCotacaoResponse:
        """Executa a consulta de cotação delegada com segurança rigorosa, autenticação e isolamento."""
        provider_slug = provider_slug_raw.strip().upper()
        commodity = commodity_raw.strip().upper()

        # 1. Proteção contra SSRF e injeção de URLs arbitrárias
        validar_ssrf_safety(provider_slug, "provedor")
        validar_ssrf_safety(commodity, "commodity")

        if provider_slug not in _PROVEDORES_PERMITIDOS:
            # Provedores comerciais conhecidos bloqueados por compliance de licença
            for prov in BYOK_PROVIDERS_CATALOG:
                if prov.slug == provider_slug and prov.status == ByokProviderStatus.DESABILITADO_LICENCA:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=(
                            f"O provedor '{prov.nome}' está desabilitado por restrições de licenciamento. "
                            f"{prov.avisoRegulatorio}"
                        ),
                    )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provedor '{provider_slug}' não suportado pelo Proxy BYOK.",
            )

        if commodity not in _COMMODITIES_PERMITIDAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Commodity '{commodity}' não permitida. Válidas: {sorted(list(_COMMODITIES_PERMITIDAS))}",
            )

        # 2. Resolução estrita da credencial do usuário no cofre individual (Envelope Encryption)
        # Se a credencial não existir ou foi revogada, a chamada é recusada imediatamente
        api_key = await self.vault.resolve_plaintext_credential(usuario_id, provider_slug)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Credencial para o provedor '{provider_slug}' inválida.",
            )

        # 3. Rate limiting por usuário e provedor
        await self.rate_limiter.check_and_increment(usuario_id, provider_slug)

        # 4. Cache isolado por usuário e provedor
        cached_quote = await self.cache.get(usuario_id, provider_slug, commodity, tipo_mercado)
        if cached_quote:
            return cached_quote

        # 5. Controle de concorrência e deduplicação single-flight por instrumento
        flight_key = f"{usuario_id}:{provider_slug}:{commodity}:{tipo_mercado.value}"
        async with self.in_flight_meta_lock:
            flight_lock = self.in_flight_locks.setdefault(flight_key, asyncio.Lock())

        async with flight_lock:
            # Re-verifica cache sob o lock
            cached_now = await self.cache.get(usuario_id, provider_slug, commodity, tipo_mercado)
            if cached_now:
                return cached_now

            # Semáforo global de concorrência por worker
            async with self.concurrency_semaphore:
                try:
                    # Timeout estrito na requisição ao provedor (Python 3.10+ compatível)
                    cotacao = await asyncio.wait_for(
                        self._execute_provider_fetch(
                            usuario_id=usuario_id,
                            provider_slug=provider_slug,
                            api_key=api_key,
                            commodity=commodity,
                            tipo_mercado=tipo_mercado,
                        ),
                        timeout=AGRO_BYOK_REQUEST_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError as exc:
                    logger.error(
                        f"Timeout de {AGRO_BYOK_REQUEST_TIMEOUT_SECONDS}s no provedor {provider_slug}",
                        user_id=str(usuario_id),
                        commodity=commodity,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail=f"Tempo limite esgotado ao consultar o provedor '{provider_slug}'.",
                    ) from exc

                # Armazena exclusivamente no cache privado do usuário
                await self.cache.set(usuario_id, provider_slug, commodity, tipo_mercado, cotacao)
                return cotacao

    async def _execute_provider_fetch(
        self,
        usuario_id: uuid.UUID,
        provider_slug: str,
        api_key: str,
        commodity: str,
        tipo_mercado: TipoMercado,
    ) -> ByokCotacaoResponse:
        """Executa a busca real ou simulada de cotação sem vazar credenciais."""
        # Titularidade explícita da consulta (identificador opaco para rastreabilidade)
        titularidade = f"BYOK-{usuario_id.hex[:8]}-{provider_slug}"
        now = datetime.now(timezone.utc)

        # Provedor SIMULATED: Contratos calibrados com distinção rigorosa FÍSICO vs FUTURO
        if provider_slug == "SIMULATED":
            # Simula latência de rede realista (10ms a 30ms)
            await asyncio.sleep(0.02)

            if commodity == "SOJA":
                if tipo_mercado == TipoMercado.FISICO:
                    return ByokCotacaoResponse(
                        commodity="SOJA",
                        instrumento="SOJA_BR_PARANAGUA_CEPEA",
                        tipoMercado=TipoMercado.FISICO,
                        valor=138.50,
                        moeda="BRL",
                        unidade="saca 60kg",
                        bolsaOuRegiao="Porto de Paranaguá/PR",
                        dataReferencia=now,
                        fonte="CEPEA/ESALQ (Homologado)",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.FECHAMENTO,
                        titularidadeByok=titularidade,
                        cached=False,
                    )
                else:
                    return ByokCotacaoResponse(
                        commodity="SOJA",
                        instrumento="CBOT:ZS",
                        tipoMercado=TipoMercado.FUTURO,
                        valor=1025.25,
                        moeda="USD_CENT",
                        unidade="bushel",
                        bolsaOuRegiao="CBOT - Chicago Board of Trade",
                        dataReferencia=now,
                        fonte="CBOT/CME Simulado",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.TEMPO_REAL,
                        titularidadeByok=titularidade,
                        cached=False,
                    )

            elif commodity == "MILHO":
                if tipo_mercado == TipoMercado.FISICO:
                    return ByokCotacaoResponse(
                        commodity="MILHO",
                        instrumento="MILHO_BR_CAMPINAS_CEPEA",
                        tipoMercado=TipoMercado.FISICO,
                        valor=68.20,
                        moeda="BRL",
                        unidade="saca 60kg",
                        bolsaOuRegiao="Campinas/SP",
                        dataReferencia=now,
                        fonte="CEPEA/ESALQ (Homologado)",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.FECHAMENTO,
                        titularidadeByok=titularidade,
                        cached=False,
                    )
                else:
                    return ByokCotacaoResponse(
                        commodity="MILHO",
                        instrumento="B3:CCM",
                        tipoMercado=TipoMercado.FUTURO,
                        valor=74.50,
                        moeda="BRL",
                        unidade="saca 60kg",
                        bolsaOuRegiao="B3 - Brasil, Bolsa, Balcão",
                        dataReferencia=now,
                        fonte="B3 Futuros Simulado",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.TEMPO_REAL,
                        titularidadeByok=titularidade,
                        cached=False,
                    )

            elif commodity == "BOI_GORDO":
                if tipo_mercado == TipoMercado.FISICO:
                    return ByokCotacaoResponse(
                        commodity="BOI_GORDO",
                        instrumento="BOI_BR_SP_CEPEA",
                        tipoMercado=TipoMercado.FISICO,
                        valor=305.00,
                        moeda="BRL",
                        unidade="@ (arroba 15kg)",
                        bolsaOuRegiao="Estado de São Paulo",
                        dataReferencia=now,
                        fonte="CEPEA/B3 (Homologado)",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.FECHAMENTO,
                        titularidadeByok=titularidade,
                        cached=False,
                    )
                else:
                    return ByokCotacaoResponse(
                        commodity="BOI_GORDO",
                        instrumento="B3:BGI",
                        tipoMercado=TipoMercado.FUTURO,
                        valor=312.80,
                        moeda="BRL",
                        unidade="@ (arroba 15kg)",
                        bolsaOuRegiao="B3 - Brasil, Bolsa, Balcão",
                        dataReferencia=now,
                        fonte="B3 Futuros Simulado",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.TEMPO_REAL,
                        titularidadeByok=titularidade,
                        cached=False,
                    )

            elif commodity == "CAFE":
                if tipo_mercado == TipoMercado.FISICO:
                    return ByokCotacaoResponse(
                        commodity="CAFE",
                        instrumento="CAFE_ARABICA_SUL_MINAS_TIPO6",
                        tipoMercado=TipoMercado.FISICO,
                        valor=1480.00,
                        moeda="BRL",
                        unidade="saca 60kg",
                        bolsaOuRegiao="Sul de Minas Gerais",
                        dataReferencia=now,
                        fonte="CEPEA/ESALQ (Homologado)",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.FECHAMENTO,
                        titularidadeByok=titularidade,
                        cached=False,
                    )
                else:
                    return ByokCotacaoResponse(
                        commodity="CAFE",
                        instrumento="ICE:KC",
                        tipoMercado=TipoMercado.FUTURO,
                        valor=254.50,
                        moeda="USD_CENT",
                        unidade="libra-peso (lb)",
                        bolsaOuRegiao="ICE Futures US",
                        dataReferencia=now,
                        fonte="ICE US Simulado",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.TEMPO_REAL,
                        titularidadeByok=titularidade,
                        cached=False,
                    )

            elif commodity == "TRIGO":
                if tipo_mercado == TipoMercado.FISICO:
                    return ByokCotacaoResponse(
                        commodity="TRIGO",
                        instrumento="TRIGO_BR_PARANA_DERAL",
                        tipoMercado=TipoMercado.FISICO,
                        valor=1340.00,
                        moeda="BRL",
                        unidade="tonelada",
                        bolsaOuRegiao="Paraná (DERAL)",
                        dataReferencia=now,
                        fonte="DERAL/SEAB-PR (Homologado)",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.FECHAMENTO,
                        titularidadeByok=titularidade,
                        cached=False,
                    )
                else:
                    return ByokCotacaoResponse(
                        commodity="TRIGO",
                        instrumento="CBOT:ZW",
                        tipoMercado=TipoMercado.FUTURO,
                        valor=585.00,
                        moeda="USD_CENT",
                        unidade="bushel",
                        bolsaOuRegiao="CBOT - Chicago Board of Trade",
                        dataReferencia=now,
                        fonte="CBOT/CME Simulado",
                        provedor=provider_slug,
                        situacao=SituacaoCotacao.TEMPO_REAL,
                        titularidadeByok=titularidade,
                        cached=False,
                    )

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Execução não suportada para o provedor '{provider_slug}'.",
        )
