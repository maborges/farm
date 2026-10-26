"""Orquestrador do serviço de indicadores macroeconômicos públicos."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import httpx
from loguru import logger
from pydantic import ValidationError

from .macro_cache import MacroCache, MacroCacheEntry
from .sgs import (
    AVISO_LEGAL_BCB,
    BcbSgsClient,
    IndicadorMacroItem,
    IndicadoresMacroPayload,
    IndicadoresMacroResponse,
    SERIE_EURO_COMPRA,
    SERIE_EURO_VENDA,
    SERIE_IPCA_12M,
    SERIE_IPCA_MENSAL,
    SERIE_META_SELIC,
    SgsObservation,
)

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def check_item_staleness(item_id: str, ref_date: date, now: datetime) -> tuple[str, bool]:
    """
    Avalia a defasagem econômica de uma série com base em sua periodicidade e calendário oficial.
    Regras:
    - EURO_PTAX (diária): Tolerância de até 5 dias corridos (fins de semana e feriados bancários).
    - SELIC_META (decisões Copom): Tolerância de até 60 dias corridos (Copom reúne a cada ~45 dias).
    - IPCA_MENSAL e IPCA_12M (mensal): Tolerância de até 65 dias corridos (divulgação pelo IBGE até o 10º dia do mês seguinte).
    """
    days = (now.date() - ref_date).days
    if days < 0:
        return ("DEFASADO", True)

    if item_id == "EURO_PTAX":
        return ("NORMAL", False) if days <= 5 else ("DEFASADO", True)
    if item_id == "SELIC_META":
        return ("NORMAL", False) if days <= 60 else ("DEFASADO", True)
    if item_id in ("IPCA_MENSAL", "IPCA_12M"):
        return ("NORMAL", False) if days <= 65 else ("DEFASADO", True)

    return ("NORMAL", False) if days <= 30 else ("DEFASADO", True)


def format_macro_response(
    payload: IndicadoresMacroPayload | None,
    consulted: datetime,
    synced: datetime | None,
    availability: str = "NORMAL",
) -> IndicadoresMacroResponse:
    if payload is None:
        return IndicadoresMacroResponse(
            sucesso=False,
            dataConsultaIso=consulted,
            cacheAtualizadoEmIso=synced,
            estadoDisponibilidade=availability,
            estaDesatualizado=True,
            avisoLegal=AVISO_LEGAL_BCB,
            itens=[],
        )

    fallback_set = set(payload.seriesFallback)
    if availability == "FONTE_INDISPONIVEL":
        fallback_set.update(["SELIC_META", "IPCA_MENSAL", "IPCA_12M", "EURO_PTAX"])

    itens: list[IndicadorMacroItem] = []

    # 1. SELIC_META
    if payload.selic:
        if "SELIC_META" in fallback_set:
            status, is_stale = "FONTE_INDISPONIVEL", True
        else:
            status, is_stale = check_item_staleness("SELIC_META", payload.selic.data, consulted)
        itens.append(
            IndicadorMacroItem(
                id="SELIC_META",
                nomeOficial="Taxa de juros - Meta Selic definida pelo Copom",
                codigoSerieBcb=SERIE_META_SELIC,
                valor=payload.selic.valor,
                unidade="% a.a.",
                periodicidade="DIARIA",
                dataReferencia=payload.selic.data.isoformat(),
                dataConsultaIso=consulted,
                fonteOficial="Banco Central do Brasil (BCB)",
                estadoDisponibilidade=status,
                estaDesatualizado=is_stale,
                avisoLegal=AVISO_LEGAL_BCB,
            )
        )

    # 2. IPCA_MENSAL
    if payload.ipca_mensal:
        if "IPCA_MENSAL" in fallback_set:
            status, is_stale = "FONTE_INDISPONIVEL", True
        else:
            status, is_stale = check_item_staleness("IPCA_MENSAL", payload.ipca_mensal.data, consulted)
        itens.append(
            IndicadorMacroItem(
                id="IPCA_MENSAL",
                nomeOficial="Índice nacional de preços ao consumidor-amplo (IPCA)",
                codigoSerieBcb=SERIE_IPCA_MENSAL,
                valor=payload.ipca_mensal.valor,
                unidade="% a.m.",
                periodicidade="MENSAL",
                dataReferencia=payload.ipca_mensal.data.isoformat(),
                dataConsultaIso=consulted,
                fonteOficial="IBGE / Banco Central do Brasil (BCB)",
                estadoDisponibilidade=status,
                estaDesatualizado=is_stale,
                avisoLegal=AVISO_LEGAL_BCB,
            )
        )

    # 3. IPCA_12M
    if payload.ipca_12m:
        if "IPCA_12M" in fallback_set:
            status, is_stale = "FONTE_INDISPONIVEL", True
        else:
            status, is_stale = check_item_staleness("IPCA_12M", payload.ipca_12m.data, consulted)
        itens.append(
            IndicadorMacroItem(
                id="IPCA_12M",
                nomeOficial="Índice nacional de preços ao consumidor-amplo (IPCA) - em 12 meses",
                codigoSerieBcb=SERIE_IPCA_12M,
                valor=payload.ipca_12m.valor,
                unidade="% em 12 meses",
                periodicidade="MENSAL",
                dataReferencia=payload.ipca_12m.data.isoformat(),
                dataConsultaIso=consulted,
                fonteOficial="IBGE / Banco Central do Brasil (BCB)",
                estadoDisponibilidade=status,
                estaDesatualizado=is_stale,
                avisoLegal=AVISO_LEGAL_BCB,
            )
        )

    # 4. EURO_PTAX
    if payload.euro_venda and payload.euro_compra:
        if "EURO_PTAX" in fallback_set:
            status, is_stale = "FONTE_INDISPONIVEL", True
        else:
            status, is_stale = check_item_staleness("EURO_PTAX", payload.euro_venda.data, consulted)
        itens.append(
            IndicadorMacroItem(
                id="EURO_PTAX",
                nomeOficial="Taxa de câmbio - Euro / Real - comercial (fechamento PTAX)",
                codigoSerieBcb=SERIE_EURO_VENDA,
                valor=payload.euro_venda.valor,
                valorVenda=payload.euro_venda.valor,
                valorCompra=payload.euro_compra.valor,
                unidade="BRL",
                periodicidade="DIARIA",
                dataReferencia=payload.euro_venda.data.isoformat(),
                dataConsultaIso=consulted,
                fonteOficial="Banco Central do Brasil (BCB)",
                estadoDisponibilidade=status,
                estaDesatualizado=is_stale,
                avisoLegal=AVISO_LEGAL_BCB,
            )
        )

    if not itens:
        return IndicadoresMacroResponse(
            sucesso=False,
            dataConsultaIso=consulted,
            cacheAtualizadoEmIso=synced,
            estadoDisponibilidade="INDISPONIVEL",
            estaDesatualizado=True,
            avisoLegal=AVISO_LEGAL_BCB,
            itens=[],
        )

    all_normal = all(it.estadoDisponibilidade == "NORMAL" for it in itens)
    all_fallback = all(it.estadoDisponibilidade == "FONTE_INDISPONIVEL" for it in itens)
    any_stale = any(it.estaDesatualizado for it in itens)

    if all_normal:
        overall_availability = "NORMAL"
    elif all_fallback:
        overall_availability = "FONTE_INDISPONIVEL"
    else:
        overall_availability = "PARCIAL"

    return IndicadoresMacroResponse(
        sucesso=True,
        dataConsultaIso=consulted,
        cacheAtualizadoEmIso=synced,
        estadoDisponibilidade=overall_availability,
        estaDesatualizado=any_stale,
        avisoLegal=AVISO_LEGAL_BCB,
        itens=itens,
    )


class IndicadoresMacroService:
    """Orquestra a leitura pública de indicadores macroeconômicos sem acesso ao PostgreSQL."""

    def __init__(self, cache: MacroCache, client: BcbSgsClient, ttl_seconds: int = 1800) -> None:
        self.cache = cache
        self.client = client
        self.ttl_seconds = max(60, min(ttl_seconds, 43200))

    async def get(self, now: datetime | None = None) -> IndicadoresMacroResponse:
        now = now or datetime.now(timezone.utc)
        shared = await self.cache.redis_ready()
        fresh = await self.cache.get_fresh(shared)
        if fresh:
            return format_macro_response(fresh.payload, now, fresh.synced_at, "NORMAL")

        last = await self._valid_last(shared, now)
        if not shared and not self.cache.single_worker_fallback:
            return format_macro_response(
                last.payload if last else None,
                now,
                last.synced_at if last else None,
                "FONTE_INDISPONIVEL" if last else "INDISPONIVEL",
            )

        token = await self.cache.acquire(shared)
        if token is None:
            return await self._wait_or_fallback(shared, last, now)

        try:
            # Dupla checagem após adquirir o lock
            fresh = await self.cache.get_fresh(shared)
            if fresh:
                return format_macro_response(fresh.payload, now, fresh.synced_at, "NORMAL")

            try:
                dict_results = await self.client.fetch_series_dict()
                series_fallback: list[str] = []

                # Selic
                selic = dict_results.get("selic")
                if not isinstance(selic, SgsObservation):
                    if last and last.payload.selic:
                        selic = last.payload.selic
                        series_fallback.append("SELIC_META")
                    else:
                        selic = None

                # IPCA Mensal
                ipca_m = dict_results.get("ipca_mensal")
                if not isinstance(ipca_m, SgsObservation):
                    if last and last.payload.ipca_mensal:
                        ipca_m = last.payload.ipca_mensal
                        series_fallback.append("IPCA_MENSAL")
                    else:
                        ipca_m = None

                # IPCA 12M
                ipca_12m = dict_results.get("ipca_12m")
                if not isinstance(ipca_12m, SgsObservation):
                    if last and last.payload.ipca_12m:
                        ipca_12m = last.payload.ipca_12m
                        series_fallback.append("IPCA_12M")
                    else:
                        ipca_12m = None

                # Euro Venda e Compra
                euro_v = dict_results.get("euro_venda")
                euro_c = dict_results.get("euro_compra")
                if not (isinstance(euro_v, SgsObservation) and isinstance(euro_c, SgsObservation)):
                    if last and last.payload.euro_venda and last.payload.euro_compra:
                        euro_v = last.payload.euro_venda
                        euro_c = last.payload.euro_compra
                        series_fallback.append("EURO_PTAX")
                    else:
                        euro_v = None
                        euro_c = None

                if not any([selic, ipca_m, ipca_12m, euro_v]):
                    return self._fallback(last, now)

                payload = IndicadoresMacroPayload(
                    selic=selic,
                    ipca_mensal=ipca_m,
                    ipca_12m=ipca_12m,
                    euro_venda=euro_v,
                    euro_compra=euro_c,
                    dataApuracaoIso=now,
                    seriesFallback=series_fallback,
                )
                entry = MacroCacheEntry(payload=payload, synced_at=datetime.now(timezone.utc))
                ttl = self._ttl(now)
                effective_ttl = ttl if not series_fallback else min(ttl, 300)
                await self.cache.save(entry, effective_ttl, shared)
                return format_macro_response(entry.payload, now, entry.synced_at, "NORMAL")
            except (httpx.HTTPError, ValueError, ValidationError, TimeoutError, OSError) as exc:
                logger.warning("BCB SGS upstream indisponível", error_type=type(exc).__name__)
                return self._fallback(last, now)
        finally:
            await self.cache.release(token, shared)

    async def _valid_last(self, shared: bool, now: datetime) -> MacroCacheEntry | None:
        entry = await self.cache.get_last(shared)
        if not entry:
            return None
        # Aceita último valor com até 30 dias de apuração
        age_days = (now.date() - entry.payload.dataApuracaoIso.date()).days
        return entry if 0 <= age_days <= 30 else None

    async def _wait_or_fallback(
        self, shared: bool, last: MacroCacheEntry | None, now: datetime
    ) -> IndicadoresMacroResponse:
        for _ in range(5):
            await asyncio.sleep(0.3)
            fresh = await self.cache.get_fresh(shared)
            if fresh:
                return format_macro_response(fresh.payload, now, fresh.synced_at, "NORMAL")
            if last:
                break
        return self._fallback(last, now)

    @staticmethod
    def _fallback(last: MacroCacheEntry | None, now: datetime) -> IndicadoresMacroResponse:
        return format_macro_response(
            last.payload if last else None,
            now,
            last.synced_at if last else None,
            "FONTE_INDISPONIVEL" if last else "INDISPONIVEL",
        )

    def _ttl(self, now: datetime) -> int:
        local = now.astimezone(SAO_PAULO)
        # Fins de semana: 4 horas
        if local.weekday() >= 5:
            return min(self.ttl_seconds * 4, 14400)
        # Dias úteis antes das 13h30 (fechamento Euro PTAX): 15 min
        if local.hour < 13 or (local.hour == 13 and local.minute < 30):
            return min(self.ttl_seconds, 900)
        # Dias úteis após fechamento do Euro: 1 hora
        return min(self.ttl_seconds * 2, 3600)
