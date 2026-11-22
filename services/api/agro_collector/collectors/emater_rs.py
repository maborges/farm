"""Coletor Nível 2 para boletim semanal PDF da EMATER/RS-ASCAR."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urljoin

from ..ai_extractor import extract_observations_with_ai
from ..contracts import CANONICAL_UNITS_BY_COMMODITY, CollectorExecutionPayload, RawObservation
from ..pdf_extractor import extract_text_from_pdf
from .base import BaseCollector, CollectorContext

_EMATER_ITEMS_SPEC: tuple[tuple[str, str, str], ...] = (
    ("leite", r"Leite\s*\(Litro\)", "Litro"),
    ("suino", r"Su[íi]no\s*\(kg\s*vivo\)", "Quilograma (kg)"),
    ("arroz", r"Arroz\s*\(50\s*kg/sc\.\)", "Saca de 50 kg"),
    ("boi-gordo", r"Boi\s*\(kg\s*vivo\)", "Quilograma (kg)"),
    ("milho", r"Milho\s*\(60\s*kg/sc\.\)", "Saca de 60 kg"),
    ("soja", r"Soja\s*\(60\s*kg/sc\.\)", "Saca de 60 kg"),
    ("vaca-em-pe", r"Vaca\s*\(kg\s*vivo\)", "Quilograma (kg)"),
    ("trigo", r"Trigo\s*\(60\s*kg/sc\.\)", "Saca de 60 kg"),
    ("feijao", r"Feij[ãa]o\s*\(60\s*kg/sc\.\)", "Saca de 60 kg"),
)


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            for k, v in attrs:
                if k.lower() == "href" and v:
                    self.hrefs.append(v.strip())


def discover_latest_emater_pdf_url(html_text: str, base_url: str) -> str | None:
    """Identifica o PDF semanal ``preco_DDMMYYYY.pdf`` mais recente na página índice.

    Args:
        html_text: HTML da página ``precos-semanais.php`` da EMATER-RS.
        base_url: URL base usada para resolver caminhos relativos.

    Returns:
        URL absoluta HTTPS do PDF mais recente ou ``None`` se ausente.
    """
    parser = _HrefParser()
    parser.feed(html_text)
    candidates: list[tuple[date, str]] = []
    for href in parser.hrefs:
        m = re.search(r"preco_(\d{2})(\d{2})(20\d{2})\.pdf", href, re.I)
        if not m:
            continue
        try:
            dt = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        candidates.append((dt, urljoin(base_url, href)))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return candidates[0][1]


def _extract_emater_ref_date(pdf_text: str) -> date:
    m_period = re.search(r"a\s+(\d{2})/(\d{2})/(20\d{2})", pdf_text)
    if m_period:
        return datetime.strptime(
            f"{m_period.group(1)}/{m_period.group(2)}/{m_period.group(3)}",
            "%d/%m/%Y",
        ).date()
    m_num = re.search(r"(\d{2})\s+de\s+novembro\s+de\s+(20\d{2})", pdf_text, re.I)
    if m_num:
        return date(int(m_num.group(2)), 11, int(m_num.group(1)))
    return date.today()


def parse_emater_rs_summary_text(pdf_text: str, documento_oficial: str) -> list[RawObservation]:
    """Parser determinístico auxiliar sobre o quadro estadual de médias da EMATER-RS.

    Args:
        pdf_text: Texto completo extraído do boletim PDF semanal.
        documento_oficial: URL oficial do documento baixado.

    Returns:
        Lista de ``RawObservation`` com trecho literal presente no ``pdf_text``.
    """
    data_ref = _extract_emater_ref_date(pdf_text)
    m_media = re.search(r"M[ée]dia\s+((?:\d+,\d{2}\s*){9,11})", pdf_text)
    if not m_media:
        return []
    nums = re.findall(r"\d+,\d{2}", m_media.group(1))
    # Ordem padrão das 11 colunas:
    # Leite, Suíno, Arroz, Boi, Búfalo, Cordeiro, Milho, Soja, Vaca, Trigo, Feijão
    col_map: list[tuple[int, str, str]] = [
        (0, "leite", "Litro"),
        (1, "suino", "Quilograma (kg)"),
        (2, "arroz", "Saca de 50 kg"),
        (3, "boi-gordo", "Quilograma (kg)"),
        (6, "milho", "Saca de 60 kg"),
        (7, "soja", "Saca de 60 kg"),
        (8, "vaca-em-pe", "Quilograma (kg)"),
        (9, "trigo", "Saca de 60 kg"),
        (10, "feijao", "Saca de 60 kg"),
    ]
    raw_snippet = m_media.group(0).strip()
    observations: list[RawObservation] = []
    for idx, cid, orig_unit in col_map:
        if idx >= len(nums):
            break
        val = Decimal(nums[idx].replace(",", "."))
        observations.append(
            RawObservation(
                commodity_id=cid,
                uf="RS",
                praca="Rio Grande do Sul — Média Estadual",
                tipo_preco="PRECO_MEDIO_RECEBIDO_PRODUTOR",
                periodicidade="SEMANAL",
                data_referencia=data_ref,
                valor_original=val,
                unidade_original=orig_unit,
                unidade_destino=CANONICAL_UNITS_BY_COMMODITY.get(cid, orig_unit),
                trecho_evidencia=raw_snippet,
                registro_origem=f"EMATER/RS | Média Estadual | {nums[idx]} {orig_unit}",
                documento_oficial=documento_oficial,
                is_media_estadual=True,
            )
        )
    return observations


class EmaterRsPdfCollector(BaseCollector):
    """Coletor Nível 2 para boletim semanal em PDF da EMATER/RS-ASCAR."""

    slug = "emater_rs"

    async def collect(self, ctx: CollectorContext) -> CollectorExecutionPayload:
        """Descobre e processa o boletim PDF semanal da EMATER-RS com IA ou fallback local.

        Args:
            ctx: Contexto de execução contendo fonte, fetcher seguro e opcional ``ia_callable``.

        Returns:
            ``CollectorExecutionPayload`` com PDF bruto, texto de evidência e telemetria IA.
        """
        target_url = ctx.source.url_principal
        first_res = await ctx.fetcher.fetch(
            target_url,
            ctx.source.dominios_whitelist,
            etag=ctx.last_etag,
            last_modified=ctx.last_modified,
        )
        if first_res.not_modified:
            return CollectorExecutionPayload(fetch_result=first_res, observations=[])

        pdf_res = first_res
        if not first_res.content[:8].lstrip().startswith(b"%PDF-"):
            html_txt = first_res.content.decode("latin-1", errors="replace")
            latest_pdf = discover_latest_emater_pdf_url(html_txt, first_res.url_efetiva)
            if latest_pdf:
                pdf_res = await ctx.fetcher.fetch(
                    latest_pdf,
                    ctx.source.dominios_whitelist,
                )

        pdf_text = extract_text_from_pdf(pdf_res.content)
        usar_ia = bool((ctx.source.config_extrator or {}).get("usar_ia", True))

        from ia.anthropic_client import has_ia_configured

        if ctx.ia_callable is not None or (usar_ia and has_ia_configured()):
            ai_res = await extract_observations_with_ai(
                pdf_text,
                source_sigla=ctx.source.sigla,
                uf_padrao=ctx.source.uf_padrao or "RS",
                documento_oficial=pdf_res.url_efetiva,
                periodicidade="SEMANAL",
                extra_instructions="Boletim semanal EMATER/RS. Extraia médias estaduais do RS.",
                ia_callable=ctx.ia_callable,
            )
            return CollectorExecutionPayload(
                fetch_result=pdf_res,
                observations=ai_res.observations,
                raw_text_for_evidence=pdf_text,
                modelo_ia=ai_res.modelo_ia,
                tokens_entrada=ai_res.tokens_entrada,
                tokens_saida=ai_res.tokens_saida,
                custo_estimado_usd=ai_res.custo_estimado_usd,
            )

        fallback_obs = parse_emater_rs_summary_text(pdf_text, pdf_res.url_efetiva)
        return CollectorExecutionPayload(
            fetch_result=pdf_res,
            observations=fallback_obs,
            raw_text_for_evidence=pdf_text,
        )
