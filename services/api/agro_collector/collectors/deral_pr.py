"""Coletor Nível 1 determinístico para DERAL/SEAB-PR (planilha oficial prp.xls)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from core.services.deral_snapshot_service import parse_deral_xls

from ..contracts import CollectorExecutionPayload, RawObservation
from .base import BaseCollector, CollectorContext


def _to_decimal(val: Any) -> Decimal:
    return Decimal(str(val))


def parse_deral_payload_observations(
    dados_xls: bytes,
    sha256_hash: str,
    documento_oficial: str,
) -> list[RawObservation]:
    """Converte bytes da planilha ``prp.xls`` do DERAL em observações canônicas.

    Args:
        dados_xls: Conteúdo binário XLS baixado do portal SEAB/PR.
        sha256_hash: Digest SHA-256 do arquivo para proveniência.
        documento_oficial: URL oficial efetiva do documento coletado.

    Returns:
        Lista de ``RawObservation`` com média estadual e núcleos regionais do PR.
    """
    parsed = parse_deral_xls(dados_xls, sha256_hash)
    data_ref = date.fromisoformat(str(parsed["dataReferencia"]))
    observations: list[RawObservation] = []

    for item in parsed.get("itens") or []:
        cid = str(item["id"])
        nome = str(item.get("commodityNome") or cid)
        unidade = str(item.get("unidade") or "")
        unidade_orig = str(item.get("unidadeOriginal") or unidade)
        reg_orig = str(item.get("registroOriginal") or "")[:120]
        valor_orig = _to_decimal(item.get("valorOriginal") or item["valor"])

        observations.append(
            RawObservation(
                commodity_id=cid,
                uf="PR",
                praca="Paraná — Média Estadual",
                tipo_preco="PRECO_MEDIO_RECEBIDO_PRODUTOR",
                periodicidade="SEMANAL",
                data_referencia=data_ref,
                valor_original=valor_orig,
                unidade_original=unidade_orig,
                unidade_destino=unidade,
                trecho_evidencia=f"{nome} | Média PR | {reg_orig} | {valor_orig} {unidade_orig}",
                registro_origem=reg_orig or None,
                documento_oficial=documento_oficial,
                is_media_estadual=True,
            )
        )

        for nucleo in item.get("pracasRegionais") or []:
            praca_nome = str(nucleo.get("praca") or "").strip()
            if not praca_nome:
                continue
            nuc_val = _to_decimal(nucleo.get("valorOriginal") or nucleo["valor"])
            nuc_reg = str(nucleo.get("registroOriginal") or reg_orig)[:120]
            observations.append(
                RawObservation(
                    commodity_id=cid,
                    uf="PR",
                    praca=praca_nome,
                    tipo_preco="PRECO_MEDIO_RECEBIDO_PRODUTOR",
                    periodicidade="SEMANAL",
                    data_referencia=data_ref,
                    valor_original=nuc_val,
                    unidade_original=unidade_orig,
                    unidade_destino=unidade,
                    trecho_evidencia=f"{nome} | {praca_nome}/PR | {nuc_reg} | {nuc_val}",
                    registro_origem=nuc_reg or None,
                    documento_oficial=documento_oficial,
                    is_media_estadual=False,
                )
            )
    return observations


class DeralPrCollector(BaseCollector):
    """Coletor oficial para médias estaduais e 20 núcleos regionais DERAL/SEAB-PR."""

    slug = "deral_pr"

    async def collect(self, ctx: CollectorContext) -> CollectorExecutionPayload:
        """Baixa e extrai cotações da planilha ``prp.xls`` mantendo ETag/If-Modified-Since.

        Args:
            ctx: Contexto de execução com fonte e ``SafeHttpFetcher``.

        Returns:
            ``CollectorExecutionPayload`` com bytes XLS e observações normalizáveis.
        """
        fetch_res = await ctx.fetcher.fetch(
            ctx.source.url_principal,
            ctx.source.dominios_whitelist,
            etag=ctx.last_etag,
            last_modified=ctx.last_modified,
        )
        if fetch_res.not_modified:
            return CollectorExecutionPayload(fetch_result=fetch_res, observations=[])

        observations = parse_deral_payload_observations(
            fetch_res.content,
            fetch_res.sha256,
            fetch_res.url_efetiva,
        )
        return CollectorExecutionPayload(fetch_result=fetch_res, observations=observations)
