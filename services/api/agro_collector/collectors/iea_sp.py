"""Coletor Nível 1 determinístico para IEA/SAA-SP (Preços Diários Recebidos SP)."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Any

from ..contracts import CANONICAL_UNITS_BY_COMMODITY, CollectorExecutionPayload, RawObservation
from ..fetcher import FetchResult, SafeHttpSession
from .base import BaseCollector, CollectorContext

IEA_BASE_URL = "https://infoiea.agricultura.sp.gov.br/BancoDeDados/PrecosDiarios/Recebidos"
MAX_LOOKBACK_BUSINESS_DAYS = 5
MAX_PAGES = 15

# Mapeamento oficial dos códigos IEA/SAA-SP para os 22 IDs canônicos do DeepFarms
IEA_COMMODITY_BY_COD: dict[str, str] = {
    "1905": "algodao",
    "1102": "amendoim",
    "1105": "arroz",
    "1411": "boi-gordo",
    "1410": "boi-magro",
    "1053": "cafe-arabica",
    "1109": "cana-de-acucar",
    "1113": "feijao",
    "1426": "frango-vivo",
    "1421": "leite",
    "1119": "mandioca-industrial",
    "1124": "milho",
    "1916": "ovo-grande",
    "1126": "soja",
    "1403": "suino",
    "1130": "trigo",
    "1412": "vaca-em-pe",
}

IEA_COMMODITY_BY_NAME: dict[str, str] = {
    "algodao em pluma": "algodao",
    "amendoim em casca": "amendoim",
    "arroz em casca": "arroz",
    "boi gordo": "boi-gordo",
    "boi magro nelore": "boi-magro",
    "cafe benef. tipo 6 duro": "cafe-arabica",
    "cana para industria": "cana-de-acucar",
    "feijao carioca": "feijao",
    "frango vivo": "frango-vivo",
    "leite cru resfriado": "leite",
    "mandioca industria": "mandioca-industrial",
    "milho": "milho",
    "ovo tipo grande branco": "ovo-grande",
    "soja": "soja",
    "suino tipo carne": "suino",
    "trigo": "trigo",
    "vaca gorda": "vaca-em-pe",
}

DEFAULT_IEA_EDR_CODES: tuple[str, ...] = tuple(f"{i:02d}" for i in range(1, 42))


@dataclass(frozen=True, slots=True)
class IeaFormMetadata:
    """Metadados extraídos da página inicial do portal IEA-SP."""

    verification_token: str
    initial_date: date
    edr_codes: tuple[str, ...]


class _IeaInputAndTableParser(HTMLParser):
    """Parser stdlib para token AntiForgery e linhas de tabela HTML do IEA-SP."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.verification_tokens: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._cur_table: list[list[str]] = []
        self._cur_row: list[str] = []
        self._cur_cell_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        t = tag.lower()
        if t == "input" and attr_map.get("name") == "__RequestVerificationToken":
            val = attr_map.get("value", "").strip()
            if val:
                self.verification_tokens.append(val)
        elif t == "table":
            self._in_table = True
            self._cur_table = []
        elif t == "tr" and self._in_table:
            self._in_row = True
            self._cur_row = []
        elif t in {"td", "th"} and self._in_row:
            self._in_cell = True
            self._cur_cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cur_cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"td", "th"} and self._in_cell:
            cell_txt = re.sub(r"\s+", " ", html.unescape("".join(self._cur_cell_parts))).strip()
            self._cur_row.append(cell_txt)
            self._in_cell = False
        elif t == "tr" and self._in_row:
            if any(self._cur_row):
                self._cur_table.append(self._cur_row)
            self._in_row = False
        elif t == "table" and self._in_table:
            if self._cur_table:
                self.tables.append(self._cur_table)
            self._in_table = False


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _normalize_label(text: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents(text)).strip().lower()


def _parse_ptbr_decimal(raw_val: str) -> Decimal | None:
    cleaned = raw_val.strip().replace(".", "").replace(",", ".")
    if not cleaned or cleaned in {"--", "-"}:
        return None
    try:
        dec = Decimal(cleaned)
    except InvalidOperation:
        return None
    return dec if dec > 0 else None


def _parse_ptbr_date(raw_date: str) -> date | None:
    try:
        return datetime.strptime(raw_date.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def extract_iea_form_metadata(
    html_text: str,
    *,
    fallback_date: date | None = None,
) -> IeaFormMetadata:
    """Extrai token AntiForgery, ``initialDate`` e EDRs do HTML GET do IEA-SP.

    Args:
        html_text: Conteúdo HTML da página ``PrecosDiarios/Recebidos``.
        fallback_date: Data alternativa se ``initialDate`` JS não estiver presente.

    Returns:
        ``IeaFormMetadata`` pronto para compor o POST AJAX.

    Raises:
        ValueError: Se o ``__RequestVerificationToken`` não for encontrado.
    """
    parser = _IeaInputAndTableParser()
    parser.feed(html_text)
    if not parser.verification_tokens:
        raise ValueError("Token __RequestVerificationToken não localizado no HTML do IEA-SP.")

    m_date = re.search(
        r"initialDate\s*=\s*new\s+Date\(\s*(\d{4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)",
        html_text,
    )
    if m_date:
        year = int(m_date.group(1))
        month_zero_based = int(m_date.group(2))
        day = int(m_date.group(3))
        init_dt = date(year, month_zero_based + 1, day)
    else:
        init_dt = fallback_date or date.today()

    edr_matches = re.findall(r'"Cod":"(\d{2})","Des":"[^"]+","Status":"ATIVO"', html_text)
    edr_codes = tuple(dict.fromkeys(edr_matches)) if edr_matches else DEFAULT_IEA_EDR_CODES
    return IeaFormMetadata(
        verification_token=parser.verification_tokens[0],
        initial_date=init_dt,
        edr_codes=edr_codes,
    )


def _extract_pagination(html_text: str) -> tuple[int, int]:
    m_rec = re.search(r"totalRecords\s*:\s*(\d+)", html_text)
    m_per = re.search(r"perPage\s*:\s*(\d+)", html_text)
    total = int(m_rec.group(1)) if m_rec else 0
    per_page = int(m_per.group(1)) if m_per else 20
    return total, max(per_page, 1)


def _build_media_estadual_observations(
    edr_observations: list[RawObservation],
    documento_oficial: str,
) -> list[RawObservation]:
    grouped: dict[tuple[str, date], list[RawObservation]] = {}
    for obs in edr_observations:
        grouped.setdefault((obs.commodity_id, obs.data_referencia), []).append(obs)

    medias: list[RawObservation] = []
    for (cid, dt), group in grouped.items():
        avg_orig = (sum(o.valor_original for o in group) / Decimal(len(group))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        sample = group[0]
        medias.append(
            RawObservation(
                commodity_id=cid,
                uf="SP",
                praca="São Paulo — Média Estadual (EDRs)",
                tipo_preco=sample.tipo_preco,
                periodicidade="DIARIA",
                data_referencia=dt,
                valor_original=avg_orig,
                unidade_original=sample.unidade_original,
                unidade_destino=sample.unidade_destino,
                trecho_evidencia=sample.trecho_evidencia,
                registro_origem=f"MEDIA_{len(group)}_EDRS_SP",
                documento_oficial=documento_oficial,
                is_media_estadual=True,
            )
        )
    return medias


def parse_iea_result_html(
    html_text: str,
    documento_oficial: str,
) -> tuple[list[RawObservation], str, int, int]:
    """Faz parse determinístico da tabela parcial HTML retornada pelo POST do IEA-SP.

    Args:
        html_text: Fragmento HTML retornado por ``PrecosDiarios/Recebidos``.
        documento_oficial: URL oficial da fonte.

    Returns:
        Tupla ``(observacoes_edr, texto_tabular_evidencia, total_records, per_page)``.
    """
    norm_full = _normalize_label(html_text)
    if "nao ha precos no periodo informado" in norm_full:
        return [], "", 0, 20

    parser = _IeaInputAndTableParser()
    parser.feed(html_text)
    edr_observations: list[RawObservation] = []
    evidence_lines: list[str] = []

    for table in parser.tables:
        for row in table:
            if len(row) < 6:
                continue
            grupo, prod_raw, edr_raw, data_raw, preco_raw, unidade_raw = row[:6]
            if _normalize_label(grupo) == "grupo":
                continue
            cid = IEA_COMMODITY_BY_NAME.get(_normalize_label(prod_raw))
            valor_orig = _parse_ptbr_decimal(preco_raw)
            data_ref = _parse_ptbr_date(data_raw)
            if not cid or valor_orig is None or data_ref is None or not edr_raw:
                continue

            row_line = f"{prod_raw} {edr_raw} {data_raw} {preco_raw} {unidade_raw}".strip()
            evidence_lines.append(row_line)
            edr_observations.append(
                RawObservation(
                    commodity_id=cid,
                    uf="SP",
                    praca=f"EDR {edr_raw}",
                    tipo_preco="PRECO_MEDIO_RECEBIDO_PRODUTOR",
                    periodicidade="DIARIA",
                    data_referencia=data_ref,
                    valor_original=valor_orig,
                    unidade_original=unidade_raw,
                    unidade_destino=CANONICAL_UNITS_BY_COMMODITY.get(cid, unidade_raw),
                    trecho_evidencia=row_line,
                    registro_origem=f"IEA-SP | {prod_raw} | {edr_raw}",
                    documento_oficial=documento_oficial,
                    is_media_estadual=False,
                )
            )

    total_records, per_page = _extract_pagination(html_text)
    return edr_observations, "\n".join(evidence_lines), total_records, per_page


def _previous_business_days(anchor: date, count: int) -> list[date]:
    days: list[date] = []
    cur = anchor
    while len(days) <= count:
        if cur.weekday() < 5:
            days.append(cur)
        cur -= timedelta(days=1)
    return days


def _build_post_pairs(
    token: str,
    target_date: date,
    product_codes: tuple[str, ...],
    edr_codes: tuple[str, ...],
    page_number: int,
) -> list[tuple[str, str]]:
    date_br = target_date.strftime("%d/%m/%Y")
    pairs: list[tuple[str, str]] = [
        ("__RequestVerificationToken", token),
        ("startDate", date_br),
        ("endDate", date_br),
        ("pageNumber", str(page_number)),
    ]
    for code in product_codes:
        pairs.append(("produtos", code))
    for edr in edr_codes:
        pairs.append(("edrs", edr))
    return pairs


async def _collect_iea_session(
    session: SafeHttpSession,
    post_url: str,
    product_codes: tuple[str, ...],
) -> tuple[FetchResult, list[RawObservation], str]:
    get_res = await session.get(post_url)
    get_html = get_res.content.decode("utf-8", errors="replace")
    meta = extract_iea_form_metadata(get_html)
    ajax_headers = {"X-Requested-With": "XMLHttpRequest"}

    last_post_res = get_res
    for target_dt in _previous_business_days(meta.initial_date, MAX_LOOKBACK_BUSINESS_DAYS):
        first_pairs = _build_post_pairs(
            meta.verification_token, target_dt, product_codes, meta.edr_codes, page_number=1
        )
        post_res = await session.post_form(post_url, first_pairs, headers=ajax_headers)
        last_post_res = post_res
        page_html = post_res.content.decode("utf-8", errors="replace")
        page_obs, page_text, total_records, per_page = parse_iea_result_html(page_html, post_url)
        if not page_obs:
            continue

        all_obs = list(page_obs)
        text_chunks = [page_text] if page_text else []
        total_pages = min(MAX_PAGES, max(1, (total_records + per_page - 1) // per_page))
        for page_num in range(2, total_pages + 1):
            next_pairs = _build_post_pairs(
                meta.verification_token, target_dt, product_codes, meta.edr_codes, page_num
            )
            next_res = await session.post_form(post_url, next_pairs, headers=ajax_headers)
            next_html = next_res.content.decode("utf-8", errors="replace")
            more_obs, more_text, _, _ = parse_iea_result_html(next_html, post_url)
            all_obs.extend(more_obs)
            if more_text:
                text_chunks.append(more_text)

        medias = _build_media_estadual_observations(all_obs, post_url)
        return post_res, all_obs + medias, "\n".join(text_chunks)

    return last_post_res, [], ""


class IeaSpCollector(BaseCollector):
    """Coletor oficial diário do IEA/SAA-SP para praças paulistas (EDRs)."""

    slug = "iea_sp"

    async def collect(self, ctx: CollectorContext) -> CollectorExecutionPayload:
        """Executa GET AntiForgery + POST AJAX por EDRs no IEA-SP com fallback de feriados.

        Args:
            ctx: Contexto de execução com fonte e ``SafeHttpFetcher``.

        Returns:
            ``CollectorExecutionPayload`` contendo observações por EDR e média estadual SP.
        """
        cfg: dict[str, Any] = ctx.source.config_extrator or {}
        configured_codes = cfg.get("product_codes")
        product_codes = (
            tuple(str(c) for c in configured_codes)
            if isinstance(configured_codes, list) and configured_codes
            else tuple(IEA_COMMODITY_BY_COD.keys())
        )
        post_url = ctx.source.url_principal or IEA_BASE_URL

        async def _runner(
            session: SafeHttpSession,
        ) -> tuple[FetchResult, list[RawObservation], str]:
            return await _collect_iea_session(session, post_url, product_codes)

        post_res, observations, raw_text = await ctx.fetcher.run_session(
            ctx.source.dominios_whitelist,
            _runner,
        )
        return CollectorExecutionPayload(
            fetch_result=post_res,
            observations=observations,
            raw_text_for_evidence=raw_text or None,
        )
