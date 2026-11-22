"""Coletor Nível 2 para boletim PDF semanal Preços Correntes da SEAPA-MG."""

from __future__ import annotations

from ..ai_extractor import extract_observations_with_ai
from ..contracts import CollectorExecutionPayload
from ..pdf_extractor import extract_text_from_pdf
from .base import BaseCollector, CollectorContext


class SeapaMgPdfCollector(BaseCollector):
    """Coletor Nível 2 IA para boletins semanais ``precos-correntes-*.pdf`` da SEAPA-MG."""

    slug = "seapa_mg"

    async def collect(self, ctx: CollectorContext) -> CollectorExecutionPayload:
        """Baixa boletim PDF da SEAPA-MG, extrai texto e aciona extrator estruturado Nível 2.

        Args:
            ctx: Contexto de execução com fonte SEAPA-MG e ``SafeHttpFetcher``.

        Returns:
            ``CollectorExecutionPayload`` sujeito à revisão humana obrigatória no Backoffice.
        """
        fetch_res = await ctx.fetcher.fetch(
            ctx.source.url_principal,
            ctx.source.dominios_whitelist,
            etag=ctx.last_etag,
            last_modified=ctx.last_modified,
        )
        if fetch_res.not_modified:
            return CollectorExecutionPayload(fetch_result=fetch_res, observations=[])

        pdf_text = extract_text_from_pdf(fetch_res.content)
        ai_res = await extract_observations_with_ai(
            pdf_text,
            source_sigla=ctx.source.sigla,
            uf_padrao=ctx.source.uf_padrao or "MG",
            documento_oficial=fetch_res.url_efetiva,
            periodicidade="SEMANAL",
            extra_instructions=(
                "Boletim SEAPA-MG Preços Correntes. Priorize praças e cotações de Minas Gerais "
                "(ex: Feijão-MG, Suíno-MG, Ovos-MG, Leite, Café, Milho, Soja) e inclua no "
                "'trecho_exato_evidencia' a menção exata da fonte/região presente no boletim."
            ),
            ia_callable=ctx.ia_callable,
        )
        return CollectorExecutionPayload(
            fetch_result=fetch_res,
            observations=ai_res.observations,
            raw_text_for_evidence=pdf_text,
            modelo_ia=ai_res.modelo_ia,
            tokens_entrada=ai_res.tokens_entrada,
            tokens_saida=ai_res.tokens_saida,
            custo_estimado_usd=ai_res.custo_estimado_usd,
        )
