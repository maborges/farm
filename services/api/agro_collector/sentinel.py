"""Agente Sentinela Nível 3 para auto-descoberta segura de novas URLs quando fontes falham."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from .fetcher import SafeHttpFetcher, UnsafeSourceUrlError, validate_source_url
from .models import AgroDataSource

_RELEVANT_EXTS = (".pdf", ".xls", ".xlsx", ".csv")
_RELEVANT_KEYWORDS = ("preco", "preço", "cotac", "cotaç", "boletim", "semanal")


class _AnchorParser(HTMLParser):
    """Extrai links ``<a href>`` e seus rótulos visíveis com stdlib."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._cur_href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        href = attr_map.get("href", "").strip()
        if href:
            self._cur_href = href
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._cur_href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._cur_href is not None:
            label = re.sub(r"\s+", " ", "".join(self._text_parts)).strip()
            self.links.append((self._cur_href, label))
            self._cur_href = None
            self._text_parts = []


def _link_score(url: str, label: str) -> tuple[int, int]:
    low = f"{url} {label}".lower()
    ext_score = 2 if any(ext in url.lower() for ext in _RELEVANT_EXTS) else 0
    kw_score = 1 if any(kw in low for kw in _RELEVANT_KEYWORDS) else 0
    m_date = re.search(r"(\d{2})[-_/]?(\d{2})[-_/](20\d{2})", url)
    date_num = (
        int(f"{m_date.group(3)}{m_date.group(2)}{m_date.group(1)}") if m_date else 0
    )
    return (ext_score + kw_score, date_num)


def discover_candidate_links(
    html_text: str,
    base_url: str,
    whitelist: Sequence[str],
    *,
    resolve_dns: bool = False,
) -> list[tuple[str, str]]:
    """Extrai e valida estritamente links candidatos dentro da whitelist da fonte.

    Args:
        html_text: Conteúdo HTML da ``url_indice`` da fonte.
        base_url: URL base para resolução de links relativos.
        whitelist: Domínios HTTPS autorizados para a fonte.
        resolve_dns: Quando ``True``, verifica DNS anti-SSRF dos hosts candidatos.

    Returns:
        Lista deduplicada ``[(url_absoluta_segura, texto_link)]`` ordenada por relevância.
    """
    parser = _AnchorParser()
    parser.feed(html_text)
    seen: set[str] = set()
    scored: list[tuple[tuple[int, int], str, str]] = []

    for href, label in parser.links:
        abs_url = urljoin(base_url, href)
        try:
            valid_url = validate_source_url(abs_url, whitelist, resolve_dns=resolve_dns)
        except UnsafeSourceUrlError:
            continue
        if valid_url in seen:
            continue
        seen.add(valid_url)
        score = _link_score(valid_url, label)
        if score[0] > 0:
            scored.append((score, valid_url, label or valid_url))

    scored.sort(key=lambda row: row[0], reverse=True)
    return [(url, label) for _score, url, label in scored[:25]]


async def run_sentinel_discovery(
    source: AgroDataSource,
    fetcher: SafeHttpFetcher,
    *,
    ia_callable: Callable[..., Awaitable[str]] | None = None,
) -> dict[str, Any] | None:
    """Inspeciona ``url_indice`` da fonte e sugere nova URL segura candidata após falhas.

    Args:
        source: Fonte institucional ou parceira que acumulou falhas consecutivas.
        fetcher: Fetcher seguro utilizado para acessar ``url_indice``.
        ia_callable: Modelo IA opcional para desempate semântico entre links validados.

    Returns:
        Dicionário estruturado com ``url_sugerida``, ``evidencia`` e timestamp, ou ``None``.
    """
    if not source.url_indice:
        return None

    res = await fetcher.fetch(source.url_indice, source.dominios_whitelist)
    html_text = res.content.decode("utf-8", errors="replace")
    candidates = discover_candidate_links(
        html_text,
        res.url_efetiva,
        source.dominios_whitelist,
        resolve_dns=fetcher.resolve_dns,
    )
    if not candidates:
        return None

    different = [(u, lbl) for u, lbl in candidates if u != source.url_principal]
    pool = different or candidates
    chosen_url, chosen_label = pool[0]

    if ia_callable is not None and len(pool) > 1:
        options_txt = "\n".join(f"- {u} ({lbl})" for u, lbl in pool[:10])
        prompt = (
            "Escolha qual link abaixo aponta para o boletim/arquivo mais recente de preços "
            f"da fonte {source.sigla}. "
            'Responda em JSON puro {"url": "...", "motivo": "..."}.\n'
            f"{options_txt}"
        )
        try:
            reply = await ia_callable(prompt, max_tokens=256, timeout=15.0)
            m = re.search(r"\{.*\}", reply, re.S)
            if m:
                parsed = json.loads(m.group(0))
                cand_url = str(parsed.get("url") or "").strip()
                valid_set = dict(pool)
                if cand_url in valid_set:
                    chosen_url = cand_url
                    chosen_label = str(parsed.get("motivo") or valid_set[cand_url])[:200]
        except Exception:
            chosen_url, chosen_label = pool[0]

    return {
        "url_sugerida": chosen_url,
        "evidencia": chosen_label[:240],
        "candidatos_avaliados": len(candidates),
        "gerado_em": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
    }
