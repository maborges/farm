"""Serviço com cache e rate limiting para os preços agropecuários públicos reais."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from .cache import PtaxCache
from .precos_publicos import (
    AVISO_LEGAL_PRECOS,
    CatalogoMercadoResponse,
    MAX_PRECOS_SEMANAIS_FRESCOS_DIAS,
    PrecoPublicoItem,
    PrecosPublicosResponse,
    carregar_catalogo_mercado,
    carregar_precos_publicos,
)


class PrecosPublicosService:
    """Orquestrador do catálogo de preços agropecuários reais de fontes públicas abertas."""

    def __init__(self, cache: PtaxCache, ttl_seconds: int = 1800) -> None:
        self.cache = cache
        self.ttl_seconds = max(300, ttl_seconds)
        self._lock = asyncio.Lock()
        self._l1_cache: PrecosPublicosResponse | None = None
        self._l1_synced_at: datetime | None = None
        self._catalogo_cache: CatalogoMercadoResponse | None = None
        self._catalogo_synced_at: datetime | None = None
        self._db_snapshot_synced_at = 0.0
        self._db_snapshot_sync_lock = asyncio.Lock()

    def _is_cache_valido(self, synced_at: datetime | None, now: datetime) -> bool:
        """Verifica se timestamp de sincronização do cache ainda está dentro do TTL."""
        if not synced_at:
            return False
        return (now - synced_at).total_seconds() < self.ttl_seconds

    def invalidate_cache(self) -> None:
        """Invalida explicitamente o cache em memória L1 de preços e catálogo."""
        self._l1_cache = None
        self._l1_synced_at = None
        self._catalogo_cache = None
        self._catalogo_synced_at = None

    async def sincronizar_snapshot_ativo(self, session: AsyncSession) -> None:
        """Reconcilia o snapshot ativo entre workers, no máximo uma vez por minuto."""
        if time.monotonic() - self._db_snapshot_synced_at < 60:
            return
        async with self._db_snapshot_sync_lock:
            if time.monotonic() - self._db_snapshot_synced_at < 60:
                return
            await self._sincronizar_snapshot_ativo(session)

    async def _sincronizar_snapshot_ativo(self, session: AsyncSession) -> None:
        """Atualiza caches de preços quando outro processo ativa uma nova semana."""
        from core.services.deral_snapshot_service import deral_snapshot_service

        snapshot_id_anterior = deral_snapshot_service.get_cached_active_snapshot_id()
        await deral_snapshot_service.sync_active_snapshot_from_db(session)
        if snapshot_id_anterior != deral_snapshot_service.get_cached_active_snapshot_id():
            self.invalidate_cache()
        self._db_snapshot_synced_at = time.monotonic()

    async def get_precos(self, now: datetime | None = None) -> PrecosPublicosResponse:
        """Retorna lista de preços reais das commodities homologadas com cache L1.

        Args:
            now: Data/hora de referência para a consulta (padrão: UTC corrente).

        Returns:
            PrecosPublicosResponse com os preços públicos verificados e metadados.

        Raises:
            Nenhum. Em caso de ausência, retorna lista vazia segura.
        """
        now = now or datetime.now(timezone.utc)
        if self._l1_cache and self._is_cache_valido(self._l1_synced_at, now):
            return self._l1_cache.model_copy(update={"dataConsultaIso": now})

        async with self._lock:
            if self._l1_cache and self._is_cache_valido(self._l1_synced_at, now):
                return self._l1_cache.model_copy(update={"dataConsultaIso": now})

            itens = carregar_precos_publicos(now)
            resposta = PrecosPublicosResponse(
                sucesso=True,
                versao="1.0",
                dataConsultaIso=now,
                cacheAtualizadoEmIso=now,
                estadoDisponibilidade=(
                    "FONTE_INDISPONIVEL"
                    if not itens
                    else "DEFASADO"
                    if any(i.defasagemDiasAproximada > MAX_PRECOS_SEMANAIS_FRESCOS_DIAS for i in itens)
                    else "NORMAL"
                ),
                avisoLegal=AVISO_LEGAL_PRECOS,
                totalItens=len(itens),
                itens=itens,
            )
            self._l1_cache = resposta
            self._l1_synced_at = now
            return resposta

    async def get_catalogo(self, now: datetime | None = None) -> CatalogoMercadoResponse:
        """Retorna o catálogo dinâmico de commodities com variantes e proveniência.

        Args:
            now: Data/hora de referência para a consulta (padrão: UTC corrente).

        Returns:
            CatalogoMercadoResponse com todas as commodities, variantes e preços.

        Raises:
            Nenhum. Resposta resiliente com fallback para referências homologadas.
        """
        now = now or datetime.now(timezone.utc)
        if self._catalogo_cache and self._is_cache_valido(self._catalogo_synced_at, now):
            return self._catalogo_cache.model_copy(update={"dataConsultaIso": now})

        async with self._lock:
            if self._catalogo_cache and self._is_cache_valido(self._catalogo_synced_at, now):
                return self._catalogo_cache.model_copy(update={"dataConsultaIso": now})

            resposta = carregar_catalogo_mercado(now)
            self._catalogo_cache = resposta
            self._catalogo_synced_at = now
            return resposta

    async def get_preco_commodity(
        self, commodity_id: str, now: datetime | None = None
    ) -> PrecoPublicoItem | None:
        """Retorna a cotação oficial de uma commodity específica por ID estável.

        Args:
            commodity_id: Identificador único estável da commodity (ex: 'soja').
            now: Data/hora de referência opcional.

        Returns:
            PrecoPublicoItem se encontrado e homologado, ou None.

        Raises:
            Nenhum.
        """
        precos = await self.get_precos(now)
        for item in precos.itens:
            if item.id == commodity_id:
                return item
        return None


def get_precos_service() -> PrecosPublicosService:
    """Helper de conveniência para obter o serviço singleton de preços públicos."""
    from .router import get_precos_service as _get_svc
    return _get_svc()

