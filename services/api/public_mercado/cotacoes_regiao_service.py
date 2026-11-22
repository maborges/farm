"""Serviço de consulta pública multi-fonte e multi-região (DERAL + IBGE/PAM + Institucionais)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agro_collector.repository import AgroMarketRepository, MarketObservationRecord

from .precos_publicos import (
    DERAL_PORTAL_URL,
    METADADOS_CATALOGO,
    PrecoPublicoItem,
    carregar_precos_publicos,
)
from .sidra import UFS, EstatisticasIbgeResponse

TipoFonteRegiao = Literal[
    "FISICO_REGIONAL",
    "MEDIA_ESTADUAL",
    "EXTREMO_REGIONAL",
    "OFICIAL_ESTADUAL",
    "PARCEIRO_AUTORIZADO",
    "ESTATISTICO_OFICIAL",
    "REFERENCIA_INSTITUCIONAL",
]

_SIGLA_PARA_CODIGO_UF: dict[str, tuple[str, str]] = {
    sigla.upper(): (code, nome) for code, (sigla, nome) in UFS.items()
}
_CODIGO_PARA_SIGLA_UF: dict[str, tuple[str, str]] = {
    code: (sigla, nome) for code, (sigla, nome) in UFS.items()
}

_MAPA_PRODUTO_SIDRA: dict[str, str] = {
    "soja": "soja",
    "milho": "milho",
    "cafe-arabica": "cafe",
    "cana-de-acucar": "cana-de-acucar",
    "trigo": "trigo",
    "arroz": "arroz",
    "feijao": "feijao",
    "feijao-preto": "feijao",
    "algodao": "algodao",
    "mandioca-industrial": "mandioca",
}

_URLS_CEPEA: dict[str, str] = {
    "soja": "https://www.cepea.org.br/br/indicador/soja.aspx",
    "milho": "https://www.cepea.org.br/br/indicador/milho.aspx",
    "boi-gordo": "https://www.cepea.org.br/br/indicador/boi-gordo.aspx",
    "cafe-arabica": "https://www.cepea.org.br/br/indicador/cafe.aspx",
    "trigo": "https://www.cepea.org.br/br/indicador/trigo.aspx",
    "arroz": "https://www.cepea.org.br/br/indicador/arroz.aspx",
    "algodao": "https://www.cepea.org.br/br/indicador/algodao.aspx",
    "leite": "https://www.cepea.org.br/br/indicador/leite.aspx",
    "frango-vivo": "https://www.cepea.org.br/br/indicador/frango.aspx",
    "suino": "https://www.cepea.org.br/br/indicador/suino.aspx",
    "mandioca-industrial": "https://www.cepea.org.br/br/indicador/mandioca.aspx",
}


class FonteCotacaoRegiaoItem(BaseModel):
    """Cotação ou canal institucional homologado para um produto em determinada região."""

    model_config = ConfigDict(extra="forbid")

    fonte_id: str
    sigla_fonte: str
    nome_fonte: str
    tipo_fonte: TipoFonteRegiao
    uf: str
    praca: str
    valor: float | None = Field(default=None, allow_inf_nan=False)
    unidade: str
    periodicidade: str
    data_referencia: str | None = None
    variacao_pct: float | None = Field(default=None, allow_inf_nan=False)
    url_consulta: str
    registro_origem: str | None = None


class ResumoMultiFonteRegiao(BaseModel):
    """Estatísticas de consenso e dispersão entre as fontes disponíveis para o produto."""

    model_config = ConfigDict(extra="forbid")

    total_fontes_catalogo: int
    fontes_com_preco_ativo: int
    valor_minimo: float | None = None
    fonte_minima: str | None = None
    valor_medio: float | None = None
    valor_maximo: float | None = None
    fonte_maxima: str | None = None
    dispersao_pct: float | None = None
    valor_recomendado_regiao: float | None = None
    fonte_recomendada_regiao: str | None = None


class CotacaoRegiaoCommodityItem(BaseModel):
    """Painel multi-fonte consolidado de uma commodity para a região consultada."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    categoria: str
    unidade: str
    uf_consulta: str
    praca_consulta: str | None = None
    fontes: list[FonteCotacaoRegiaoItem] = Field(default_factory=list)
    resumo: ResumoMultiFonteRegiao


class CotacoesRegiaoResponse(BaseModel):
    """Envelope de resposta da consulta pública por produto, região e fonte."""

    model_config = ConfigDict(extra="forbid")

    sucesso: bool = True
    versao: str = "1.0"
    dataConsultaIso: datetime
    uf: str
    praca: str | None = None
    fonte_filtro: str | None = None
    totalItens: int
    itens: list[CotacaoRegiaoCommodityItem] = Field(default_factory=list)


def resolver_uf_consulta(uf_raw: str | None) -> tuple[str, str, str]:
    """Normaliza sigla ou código IBGE da UF retornando (sigla, codigo_ibge, nome)."""
    limpo = str(uf_raw or "PR").strip().upper()
    if limpo in _SIGLA_PARA_CODIGO_UF:
        cod, nome = _SIGLA_PARA_CODIGO_UF[limpo]
        return limpo, cod, nome
    if limpo in _CODIGO_PARA_SIGLA_UF:
        sigla, nome = _CODIGO_PARA_SIGLA_UF[limpo]
        return sigla, limpo, nome
    return "PR", "41", "Paraná"


def _converter_kg_para_unidade(valor_kg: float, unidade: str) -> float:
    """Converte valor em R$/kg (PAM/IBGE) para a unidade comercial do produto."""
    u_low = unidade.lower()
    if "60 kg" in u_low:
        return round(valor_kg * 60.0, 2)
    if "25 kg" in u_low:
        return round(valor_kg * 25.0, 2)
    if "arroba" in u_low or "15 kg" in u_low:
        return round(valor_kg * 15.0, 2)
    if "tonelada" in u_low or "1.000 kg" in u_low:
        return round(valor_kg * 1000.0, 2)
    return round(valor_kg, 2)


def _extrair_preco_pam_ibge(
    resp: EstatisticasIbgeResponse | None, unidade: str
) -> tuple[float | None, str | None]:
    """Calcula valor unitário comercial a partir de VALOR_PRODUCAO / PRODUCAO da PAM."""
    if not resp or not resp.sucesso:
        return None, None
    ind_prod = next((i for i in resp.indicadores if i.id == "PRODUCAO"), None)
    ind_val = next((i for i in resp.indicadores if i.id == "VALOR_PRODUCAO"), None)
    if not ind_prod or not ind_val:
        return None, None
    mapa_val = {p.periodo: p.valor for p in ind_val.pontos if p.valor and p.valor > 0}
    for ponto in reversed(ind_prod.pontos):
        val_mil = mapa_val.get(ponto.periodo)
        if ponto.valor and ponto.valor > 0 and val_mil and val_mil > 0:
            valor_kg = float(val_mil) / float(ponto.valor)
            return _converter_kg_para_unidade(valor_kg, unidade), ponto.periodo
    return None, None


def _montar_fontes_deral(
    preco: PrecoPublicoItem | None, praca_filtro: str | None
) -> list[FonteCotacaoRegiaoItem]:
    """Constrói itens de fonte a partir dos Núcleos Regionais e Média Estadual DERAL."""
    if not preco:
        return []
    fontes: list[FonteCotacaoRegiaoItem] = []
    praca_norm = (praca_filtro or "").strip().casefold()
    for p in preco.pracasRegionais:
        if not praca_norm or praca_norm in p.praca.casefold():
            fontes.append(
                FonteCotacaoRegiaoItem(
                    fonte_id=f"deral-nucleo-{p.praca.lower().replace(' ', '-')}",
                    sigla_fonte="DERAL/SEAB-PR",
                    nome_fonte=f"DERAL/SEAB-PR — Núcleo {p.praca}",
                    tipo_fonte="FISICO_REGIONAL",
                    uf="PR",
                    praca=f"{p.praca}/PR",
                    valor=p.valor,
                    unidade=preco.unidade,
                    periodicidade="SEMANAL",
                    data_referencia=preco.dataReferencia,
                    variacao_pct=preco.variacaoSemanalPct,
                    url_consulta=DERAL_PORTAL_URL,
                    registro_origem=p.registroOriginal,
                )
            )
    fontes.append(
        FonteCotacaoRegiaoItem(
            fonte_id="deral-media-pr",
            sigla_fonte="DERAL/SEAB-PR",
            nome_fonte="DERAL/SEAB-PR — Média Estadual PR",
            tipo_fonte="MEDIA_ESTADUAL",
            uf="PR",
            praca="Paraná — Média Estadual (20 núcleos)",
            valor=preco.valor,
            unidade=preco.unidade,
            periodicidade="SEMANAL",
            data_referencia=preco.dataReferencia,
            variacao_pct=preco.variacaoSemanalPct,
            url_consulta=DERAL_PORTAL_URL,
            registro_origem=preco.registroOriginal,
        )
    )
    if preco.valorMinimoRegional and preco.pracaMinimoRegional:
        fontes.append(
            FonteCotacaoRegiaoItem(
                fonte_id="deral-min-pr",
                sigla_fonte="DERAL/SEAB-PR",
                nome_fonte=f"DERAL/SEAB-PR — Mínima Regional ({preco.pracaMinimoRegional})",
                tipo_fonte="EXTREMO_REGIONAL",
                uf="PR",
                praca=f"{preco.pracaMinimoRegional}/PR (Mínimo Estadual)",
                valor=preco.valorMinimoRegional,
                unidade=preco.unidade,
                periodicidade="SEMANAL",
                data_referencia=preco.dataReferencia,
                url_consulta=DERAL_PORTAL_URL,
            )
        )
    if preco.valorMaximoRegional and preco.pracaMaximoRegional:
        fontes.append(
            FonteCotacaoRegiaoItem(
                fonte_id="deral-max-pr",
                sigla_fonte="DERAL/SEAB-PR",
                nome_fonte=f"DERAL/SEAB-PR — Máxima Regional ({preco.pracaMaximoRegional})",
                tipo_fonte="EXTREMO_REGIONAL",
                uf="PR",
                praca=f"{preco.pracaMaximoRegional}/PR (Máximo Estadual)",
                valor=preco.valorMaximoRegional,
                unidade=preco.unidade,
                periodicidade="SEMANAL",
                data_referencia=preco.dataReferencia,
                url_consulta=DERAL_PORTAL_URL,
            )
        )
    return fontes


def _montar_fontes_institucionais(cid: str, unidade: str, uf_sigla: str) -> list[FonteCotacaoRegiaoItem]:
    """Adiciona canais oficiais nacionais/estaduais (CEPEA, CONAB, IMEA) da commodity."""
    fontes: list[FonteCotacaoRegiaoItem] = []
    if cid in _URLS_CEPEA:
        fontes.append(
            FonteCotacaoRegiaoItem(
                fonte_id=f"cepea-{cid}",
                sigla_fonte="CEPEA/ESALQ",
                nome_fonte="Indicador CEPEA/ESALQ — USP",
                tipo_fonte="REFERENCIA_INSTITUCIONAL",
                uf="BR",
                praca="Referência Física Nacional / Porto",
                valor=None,
                unidade=unidade,
                periodicidade="DIARIA",
                url_consulta=_URLS_CEPEA[cid],
            )
        )
    fontes.append(
        FonteCotacaoRegiaoItem(
            fonte_id=f"conab-{cid}",
            sigla_fonte="CONAB/MAPA",
            nome_fonte="CONAB — Preços Agropecuários Oficiais",
            tipo_fonte="REFERENCIA_INSTITUCIONAL",
            uf=uf_sigla,
            praca=f"Levantamento Federal ({uf_sigla} / Brasil)",
            valor=None,
            unidade=unidade,
            periodicidade="MENSAL",
            url_consulta="https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/precos-agropecuarios",
        )
    )
    return fontes


def _calcular_resumo_fontes(
    fontes: list[FonteCotacaoRegiaoItem],
    uf_sigla: str,
    praca_filtro: str | None,
) -> ResumoMultiFonteRegiao:
    """Calcula mínima, média, máxima, dispersão (%) e cotação recomendada para a região."""
    com_preco = [f for f in fontes if f.valor is not None and f.valor > 0]
    if not com_preco:
        return ResumoMultiFonteRegiao(
            total_fontes_catalogo=len(fontes),
            fontes_com_preco_ativo=0,
        )
    f_min = min(com_preco, key=lambda x: float(x.valor or 0))
    f_max = max(com_preco, key=lambda x: float(x.valor or 0))
    vals = [float(f.valor) for f in com_preco if f.valor is not None]
    media = round(sum(vals) / len(vals), 2)
    v_min = round(float(f_min.valor or 0), 2)
    v_max = round(float(f_max.valor or 0), 2)
    disp = round(((v_max - v_min) / media) * 100.0, 2) if media > 0 and len(vals) > 1 else 0.0
    recomendada = com_preco[0]
    if praca_filtro:
        p_low = praca_filtro.strip().casefold()
        match_praca = next((f for f in com_preco if p_low in f.praca.casefold()), None)
        if match_praca:
            recomendada = match_praca
    elif uf_sigla != "PR":
        match_uf = next((f for f in com_preco if f.uf == uf_sigla), None)
        if match_uf:
            recomendada = match_uf
    return ResumoMultiFonteRegiao(
        total_fontes_catalogo=len(fontes),
        fontes_com_preco_ativo=len(com_preco),
        valor_minimo=v_min,
        fonte_minima=f"{f_min.sigla_fonte} ({f_min.praca})",
        valor_medio=media,
        valor_maximo=v_max,
        fonte_maxima=f"{f_max.sigla_fonte} ({f_max.praca})",
        dispersao_pct=disp,
        valor_recomendado_regiao=recomendada.valor,
        fonte_recomendada_regiao=f"{recomendada.sigla_fonte} — {recomendada.praca}",
    )


def _converter_obs_coletor_para_fonte(
    rec: MarketObservationRecord,
    ref_today: date,
) -> tuple[int, FonteCotacaoRegiaoItem]:
    """Converte registro de ``agro_market_observations`` em ``FonteCotacaoRegiaoItem`` com rank."""
    defasado = (ref_today - rec.data_referencia).days > rec.max_defasagem_dias
    if rec.tipo_licenca == "PARCEIRO_AUTORIZADO":
        tipo_fonte: TipoFonteRegiao = "PARCEIRO_AUTORIZADO"
        rank = 4 if defasado else 2
    else:
        tipo_fonte = "OFICIAL_ESTADUAL"
        is_media = "Média Estadual" in rec.praca or rec.praca == rec.uf
        rank = 4 if defasado else (0 if is_media else 1)

    item = FonteCotacaoRegiaoItem(
        fonte_id=f"{rec.source_slug}-{rec.commodity_id}-{rec.uf.lower()}-{rec.id.hex[:6]}",
        sigla_fonte=rec.sigla_fonte,
        nome_fonte=f"{rec.sigla_fonte} — {rec.praca}",
        tipo_fonte=tipo_fonte,
        uf=rec.uf,
        praca=rec.praca,
        valor=round(float(rec.valor), 2),
        unidade=rec.unidade,
        periodicidade=rec.periodicidade,
        data_referencia=rec.data_referencia.isoformat(),
        variacao_pct=round(float(rec.variacao_pct), 2) if rec.variacao_pct is not None else None,
        url_consulta=rec.url_principal,
        registro_origem=rec.registro_origem,
    )
    return rank, item


def _rank_fonte_catalogo(
    item: FonteCotacaoRegiaoItem,
    uf_sigla: str,
    praca_filtro: str | None,
) -> int:
    """Define prioridade canônica de exibição: UF estadual > Parceiro > IBGE > Ref externa."""
    if praca_filtro and praca_filtro.strip().casefold() in item.praca.casefold():
        return -1
    if item.tipo_fonte == "OFICIAL_ESTADUAL" and item.uf == uf_sigla:
        return 0 if "Média Estadual" in item.praca else 1
    if item.tipo_fonte == "PARCEIRO_AUTORIZADO" and item.uf == uf_sigla:
        return 2
    if item.uf == uf_sigla and item.tipo_fonte in {"MEDIA_ESTADUAL", "FISICO_REGIONAL"}:
        return 0
    if item.tipo_fonte == "ESTATISTICO_OFICIAL":
        return 5
    if item.tipo_fonte in {"MEDIA_ESTADUAL", "FISICO_REGIONAL", "EXTREMO_REGIONAL"}:
        return 6
    return 7


class CotacaoMultiFonteService:
    """Agrega e compara múltiplas fontes de cotação por produto e região (UF/Praça/Município)."""

    def __init__(
        self,
        sidra_service: Any | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self.sidra_service = sidra_service
        self.session = session

    async def _obter_fonte_ibge(
        self,
        cid: str,
        unidade: str,
        localidade: tuple[str, str, str, str | None],
    ) -> FonteCotacaoRegiaoItem | None:
        slug_sidra = _MAPA_PRODUTO_SIDRA.get(cid)
        if not slug_sidra or self.sidra_service is None:
            return None
        uf_sigla, uf_cod, uf_nome, municipio_ibge = localidade
        nivel = "MUNICIPIO" if municipio_ibge else "UF"
        try:
            resp = await self.sidra_service.get_estatisticas(
                produto_id=slug_sidra,
                nivel=nivel,
                uf=uf_cod,
                municipio=municipio_ibge,
                anos=3,
            )
            valor_conv, ano_ref = _extrair_preco_pam_ibge(resp, unidade)
            if valor_conv is None:
                return None
            nome_loc = resp.localidade.nome if resp and resp.localidade else f"{uf_nome} ({uf_sigla})"
            return FonteCotacaoRegiaoItem(
                fonte_id=f"ibge-pam-{uf_sigla.lower()}-{municipio_ibge or 'uf'}",
                sigla_fonte="IBGE/SIDRA (PAM)",
                nome_fonte=f"IBGE/SIDRA — Valor Médio Regional ({nome_loc})",
                tipo_fonte="ESTATISTICO_OFICIAL",
                uf=uf_sigla,
                praca=f"{nome_loc} (Média Regional PAM/IBGE)",
                valor=valor_conv,
                unidade=unidade,
                periodicidade="ANUAL",
                data_referencia=ano_ref,
                url_consulta=resp.urlTabela if resp else "https://sidra.ibge.gov.br/tabela/5457",
                registro_origem="SIDRA!T5457(V215/V214)",
            )
        except Exception:
            return None

    async def consultar(
        self,
        produto: str | None = None,
        uf: str = "PR",
        praca: str | None = None,
        municipio_ibge: str | None = None,
        fonte: str | None = None,
        incluir_ibge: bool = True,
    ) -> CotacoesRegiaoResponse:
        """Consulta e consolida cotações por produto, região (UF/Praça/Município) e fonte."""
        now = datetime.now(timezone.utc)
        uf_sigla, uf_cod, uf_nome = resolver_uf_consulta(uf)
        precos_map = {item.id: item for item in carregar_precos_publicos(now)}
        prod_norm = (produto or "").strip().lower().replace("_", "-")
        metas = [
            m for m in METADADOS_CATALOGO
            if not prod_norm or str(m["id"]) == prod_norm
        ]
        obs_por_cid: dict[str, list[tuple[int, FonteCotacaoRegiaoItem]]] = {}
        if self.session is not None:
            collected = await AgroMarketRepository(self.session).listar_ultimas_observacoes(
                uf=uf_sigla,
                commodity_ids=[str(m["id"]) for m in metas] if prod_norm else None,
                tipo_licenca_in=["DADO_PUBLICO_GOV", "PARCEIRO_AUTORIZADO"],
            )
            ref_today = now.date()
            for rec in collected:
                if rec.source_slug == "deral_pr" and rec.commodity_id in precos_map:
                    continue
                obs_por_cid.setdefault(rec.commodity_id, []).append(
                    _converter_obs_coletor_para_fonte(rec, ref_today)
                )

        itens_resp: list[CotacaoRegiaoCommodityItem] = []
        for idx, meta in enumerate(metas):
            cid = str(meta["id"])
            preco = precos_map.get(cid)
            unidade = str(preco.unidade if preco else meta["defaultUnidade"])
            fontes = _montar_fontes_deral(preco, praca)
            collected_cid = sorted(
                obs_por_cid.get(cid, []),
                key=lambda pair: (pair[0], pair[1].praca),
            )
            fontes_frescas = [f for rank, f in collected_cid if rank < 4]
            fontes_defasadas = [f for rank, f in collected_cid if rank >= 4]
            # Consulta IBGE PAM quando filtrado por produto ou para os itens principais
            f_ibge: FonteCotacaoRegiaoItem | None = None
            if incluir_ibge and (prod_norm or idx < 8):
                f_ibge = await self._obter_fonte_ibge(
                    cid, unidade, (uf_sigla, uf_cod, uf_nome, municipio_ibge)
                )

            if uf_sigla == "PR":
                combinadas = [*fontes_frescas, *fontes, *fontes_defasadas]
                if f_ibge:
                    combinadas.append(f_ibge)
            else:
                combinadas = [*fontes_frescas, *fontes_defasadas]
                if f_ibge:
                    combinadas.append(f_ibge)
                combinadas.extend(fontes)

            combinadas.extend(_montar_fontes_institucionais(cid, unidade, uf_sigla))
            if fonte and fonte.upper() != "TODAS":
                f_up = fonte.upper()
                combinadas = [
                    f
                    for f in combinadas
                    if f_up in f.sigla_fonte.upper() or f_up in f.fonte_id.upper()
                ]
            else:
                combinadas.sort(key=lambda item: _rank_fonte_catalogo(item, uf_sigla, praca))

            resumo = _calcular_resumo_fontes(combinadas, uf_sigla, praca)
            itens_resp.append(
                CotacaoRegiaoCommodityItem(
                    id=cid,
                    nome=str(meta["nome"]),
                    categoria=str(meta["categoria"]),
                    unidade=unidade,
                    uf_consulta=uf_sigla,
                    praca_consulta=praca,
                    fontes=combinadas,
                    resumo=resumo,
                )
            )
        return CotacoesRegiaoResponse(
            sucesso=True,
            versao="1.0",
            dataConsultaIso=now,
            uf=uf_sigla,
            praca=praca,
            fonte_filtro=fonte,
            totalItens=len(itens_resp),
            itens=itens_resp,
        )
