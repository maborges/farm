"""Coletor genérico configurável para Parceiros Autorizados (CSV, PDF ou HTML via IA)."""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Any

from ..ai_extractor import extract_observations_with_ai
from ..contracts import (
    CANONICAL_COMMODITY_IDS,
    CANONICAL_UNITS_BY_COMMODITY,
    CollectorExecutionPayload,
    PeriodicidadeLiteral,
    RawObservation,
)
from ..pdf_extractor import extract_text_from_pdf
from .base import BaseCollector, CollectorContext

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class _HtmlTextStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if clean:
            self.parts.append(clean)


def _sanitize_text_cell(value: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned.startswith(_FORMULA_PREFIXES):
        return f"'{cleaned}"
    return cleaned


def _parse_flexible_decimal(raw_val: str) -> Decimal | None:
    cleaned = str(raw_val or "").strip().replace("R$", "").strip()
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        dec = Decimal(cleaned)
    except InvalidOperation:
        return None
    return dec if dec > 0 else None


def _parse_flexible_date(raw_dt: str) -> date:
    s = str(raw_dt or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return datetime.now().date()


def _parse_partner_csv(
    csv_bytes: bytes,
    ctx: CollectorContext,
    documento_oficial: str,
) -> tuple[list[RawObservation], str]:
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    sample = "\n".join(text.splitlines()[:5])
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    cfg: dict[str, Any] = ctx.source.config_extrator or {}
    col_commodity = str(cfg.get("col_commodity") or "commodity_id")
    col_valor = str(cfg.get("col_valor") or "valor")
    col_unidade = str(cfg.get("col_unidade") or "unidade")
    col_praca = str(cfg.get("col_praca") or "praca")
    col_uf = str(cfg.get("col_uf") or "uf")
    col_data = str(cfg.get("col_data") or "data_referencia")
    commodity_map = cfg.get("commodity_map") if isinstance(cfg.get("commodity_map"), dict) else {}
    periodicidade: PeriodicidadeLiteral = (
        "DIARIA"
        if cfg.get("periodicidade") == "DIARIA"
        else ("MENSAL" if cfg.get("periodicidade") == "MENSAL" else "SEMANAL")
    )

    observations: list[RawObservation] = []
    evidence_lines: list[str] = []

    for row in reader:
        raw_comm = str(row.get(col_commodity) or "").strip()
        mapped_cid = str(commodity_map.get(raw_comm, raw_comm)).strip().lower().replace("_", "-")
        if mapped_cid not in CANONICAL_COMMODITY_IDS:
            mapped_cid = raw_comm.lower()
        val = _parse_flexible_decimal(str(row.get(col_valor) or ""))
        if val is None or not raw_comm:
            continue

        uf_val = _sanitize_text_cell(str(row.get(col_uf) or ctx.source.uf_padrao))[:2].upper()
        praca_val = _sanitize_text_cell(
            str(row.get(col_praca) or ctx.source.praca_padrao or ctx.source.sigla)
        )[:120]
        default_unit = CANONICAL_UNITS_BY_COMMODITY.get(mapped_cid, "Saca de 60 kg")
        unit_val = _sanitize_text_cell(str(row.get(col_unidade) or default_unit))[:60]
        dt_val = _parse_flexible_date(str(row.get(col_data) or ""))
        raw_val_str = str(row.get(col_valor) or "").strip()
        line_evid = f"{_sanitize_text_cell(raw_comm)} {praca_val} {raw_val_str} {unit_val}".strip()
        evidence_lines.append(line_evid)

        observations.append(
            RawObservation(
                commodity_id=mapped_cid,
                uf=uf_val,
                praca=praca_val,
                tipo_preco="PRECO_MEDIO_RECEBIDO_PRODUTOR",
                periodicidade=periodicidade,
                data_referencia=dt_val,
                valor_original=val,
                unidade_original=unit_val,
                unidade_destino=CANONICAL_UNITS_BY_COMMODITY.get(mapped_cid, unit_val),
                trecho_evidencia=line_evid,
                registro_origem=f"{ctx.source.sigla} | CSV | {praca_val}"[:120],
                documento_oficial=documento_oficial,
            )
        )
    return observations, "\n".join(evidence_lines)


class GenericPartnerCollector(BaseCollector):
    """Coletor configurável para cooperativas, sindicatos e centros regionais parceiros."""

    slug = "generic_partner"

    async def collect(self, ctx: CollectorContext) -> CollectorExecutionPayload:
        """Executa coleta genérica de ``PARCEIRO_AUTORIZADO`` (CSV determinístico ou PDF/HTML IA).

        Args:
            ctx: Contexto de execução com metadados de configuração em ``config_extrator``.

        Returns:
            ``CollectorExecutionPayload`` pronto para validação e quarentena no Backoffice.
        """
        fetch_res = await ctx.fetcher.fetch(
            ctx.source.url_principal,
            ctx.source.dominios_whitelist,
            etag=ctx.last_etag,
            last_modified=ctx.last_modified,
        )
        if fetch_res.not_modified:
            return CollectorExecutionPayload(fetch_result=fetch_res, observations=[])

        cfg: dict[str, Any] = ctx.source.config_extrator or {}
        fmt = str(cfg.get("formato") or "").strip().lower()
        ct = (fetch_res.content_type or "").lower()
        if not fmt:
            if fetch_res.content[:8].lstrip().startswith(b"%PDF-") or "pdf" in ct:
                fmt = "pdf"
            elif "csv" in ct or fetch_res.url_efetiva.lower().endswith(".csv"):
                fmt = "csv"
            else:
                fmt = "html"

        if fmt == "csv":
            obs, evidence_txt = _parse_partner_csv(
                fetch_res.content, ctx, fetch_res.url_efetiva
            )
            return CollectorExecutionPayload(
                fetch_result=fetch_res,
                observations=obs,
                raw_text_for_evidence=evidence_txt,
            )

        if fmt == "pdf":
            raw_text = extract_text_from_pdf(fetch_res.content)
        else:
            stripper = _HtmlTextStripper()
            stripper.feed(fetch_res.content.decode("utf-8", errors="replace"))
            raw_text = re.sub(r"\s+", " ", " ".join(stripper.parts)).strip()

        periodicidade: PeriodicidadeLiteral = (
            "DIARIA"
            if cfg.get("periodicidade") == "DIARIA"
            else ("MENSAL" if cfg.get("periodicidade") == "MENSAL" else "SEMANAL")
        )
        ai_res = await extract_observations_with_ai(
            raw_text,
            source_sigla=ctx.source.sigla,
            uf_padrao=ctx.source.uf_padrao,
            documento_oficial=fetch_res.url_efetiva,
            periodicidade=periodicidade,
            extra_instructions=(
                str(cfg.get("prompt_instrucoes")) if cfg.get("prompt_instrucoes") else None
            ),
            ia_callable=ctx.ia_callable,
        )
        return CollectorExecutionPayload(
            fetch_result=fetch_res,
            observations=ai_res.observations,
            raw_text_for_evidence=raw_text,
            modelo_ia=ai_res.modelo_ia,
            tokens_entrada=ai_res.tokens_entrada,
            tokens_saida=ai_res.tokens_saida,
            custo_estimado_usd=ai_res.custo_estimado_usd,
        )
