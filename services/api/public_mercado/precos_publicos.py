"""Contratos e carregamento do catálogo oficial e preços públicos DERAL/SEAB-PR."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoPrecoAgro = Literal[
    "PRECO_MEDIO_RECEBIDO_PRODUTOR",
    "PRECO_MEDIO_ATACADO",
    "REFERENCIA_OFICIAL_GOVERNAMENTAL",
]

CategoriaCommodity = Literal[
    "GRAOS_CEREAIS",
    "CAFE",
    "PECUARIA",
    "LEGUMINOSAS",
    "FIBRAS",
    "HORTIFRUTI",
    "CANA_DERIVADOS",
    "OUTROS",
]

AVISO_LEGAL_PRECOS = (
    "Preço médio semanal recebido pelo produtor, publicado pelo DERAL/SEAB-PR. "
    "Não constitui cotação em tempo real nem contrato futuro."
)
MAX_PRECOS_SEMANAIS_FRESCOS_DIAS = 14
SNAPSHOT_PATH = Path(__file__).with_name("data") / "deral-prp-2026-10-16.json"
DERAL_PORTAL_URL = "https://www.agricultura.pr.gov.br/deral/precos"
DERAL_SPREADSHEET_URL = "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls"


class PracaRegionalDeralItem(BaseModel):
    """Cotação auditada de um Núcleo Regional na planilha DERAL/SEAB-PR."""

    model_config = ConfigDict(extra="forbid")

    praca: str
    valor: float = Field(gt=0, allow_inf_nan=False)
    valorOriginal: float = Field(gt=0, allow_inf_nan=False)
    registroOriginal: str


class PrecoPublicoItem(BaseModel):
    """Preço público acompanhado de proveniência até a célula de origem."""

    model_config = ConfigDict(extra="forbid")

    id: str
    commodityNome: str
    produtoOriginal: str
    classificacao: str
    valor: float = Field(gt=0, allow_inf_nan=False)
    moeda: str = "BRL"
    unidade: str
    pracaReferencia: str
    fonteOficial: str
    siglaFonte: str
    linkOficial: str
    urlConsultaInstitucional: str = DERAL_PORTAL_URL
    urlDocumentoDownload: str | None = DERAL_SPREADSHEET_URL
    tipoPreco: TipoPrecoAgro = "PRECO_MEDIO_RECEBIDO_PRODUTOR"
    periodicidade: Literal["SEMANAL", "MENSAL", "DIARIA"] = "SEMANAL"
    dataReferencia: str
    dataConsultaIso: datetime
    defasagemDiasAproximada: int = Field(ge=0)
    indicacaoTemporal: str
    avisoLegal: str = AVISO_LEGAL_PRECOS
    documentoOficial: str
    documentoHashSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataPublicacao: str | None = None
    registroOriginal: str
    valorOriginal: float = Field(gt=0, allow_inf_nan=False)
    unidadeOriginal: str
    transformacaoAplicada: str
    valorSemanaAnterior: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    variacaoSemanalAbsoluta: float | None = Field(default=None, allow_inf_nan=False)
    variacaoSemanalPct: float | None = Field(default=None, allow_inf_nan=False)
    valorMinimoRegional: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    pracaMinimoRegional: str | None = None
    valorMaximoRegional: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    pracaMaximoRegional: str | None = None
    pracasRegionais: list[PracaRegionalDeralItem] = Field(default_factory=list)


class PrecosPublicosResponse(BaseModel):
    """Resposta consolidada dos preços cuja proveniência foi validada."""

    model_config = ConfigDict(extra="forbid")

    sucesso: bool = True
    versao: str = "1.0"
    dataConsultaIso: datetime
    cacheAtualizadoEmIso: datetime | None = None
    estadoDisponibilidade: Literal["NORMAL", "DEFASADO", "FONTE_INDISPONIVEL"] = "NORMAL"
    avisoLegal: str = AVISO_LEGAL_PRECOS
    totalItens: int | None = None
    itens: list[PrecoPublicoItem] = Field(default_factory=list)


class VariantePreco(BaseModel):
    """Variante de preço por fonte, região ou modalidade comercial."""

    model_config = ConfigDict(extra="forbid")

    varianteId: str
    siglaFonte: str
    fonteOficial: str
    tipoPreco: str
    pracaReferencia: str
    unidade: str
    moeda: str = "BRL"
    valor: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    valorOriginal: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    unidadeOriginal: str | None = None
    dataReferencia: str | None = None
    dataPublicacao: str | None = None
    defasagemDiasAproximada: int | None = Field(default=None, ge=0)
    documentoOficial: str | None = None
    documentoHashSha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    registroOriginal: str | None = None
    estadoDisponibilidade: Literal["DISPONIVEL", "DEFASADO", "LINK_HOMOLOGADO"] = "DISPONIVEL"
    urlConsultaInstitucional: str
    urlDocumentoDownload: str | None = None
    valorSemanaAnterior: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    variacaoSemanalAbsoluta: float | None = Field(default=None, allow_inf_nan=False)
    variacaoSemanalPct: float | None = Field(default=None, allow_inf_nan=False)
    valorMinimoRegional: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    pracaMinimoRegional: str | None = None
    valorMaximoRegional: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    pracaMaximoRegional: str | None = None
    pracasRegionais: list[PracaRegionalDeralItem] = Field(default_factory=list)


class CommodityCatalogoItem(BaseModel):
    """Item do catálogo de mercado orientado a dados com preços e referências."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    categoria: CategoriaCommodity
    classificacao: str
    classificacaoAgronomica: str
    descricao: str
    destaque: bool = False
    tipoIndicador: str = "FISICO_SPOT"
    pracaReferencia: str
    fontePrincipalNome: str
    siglaFonte: str
    urlConsultaInstitucional: str
    urlDocumentoDownload: str | None = None
    valor: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    moeda: str = "BRL"
    unidade: str
    dataReferencia: str | None = None
    dataPublicacao: str | None = None
    defasagemDiasAproximada: int | None = Field(default=None, ge=0)
    documentoOficial: str | None = None
    documentoHashSha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    registroOriginal: str | None = None
    estadoDisponibilidade: Literal["DISPONIVEL", "DEFASADO", "LINK_HOMOLOGADO"] = "DISPONIVEL"
    valorSemanaAnterior: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    variacaoSemanalAbsoluta: float | None = Field(default=None, allow_inf_nan=False)
    variacaoSemanalPct: float | None = Field(default=None, allow_inf_nan=False)
    valorMinimoRegional: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    pracaMinimoRegional: str | None = None
    valorMaximoRegional: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    pracaMaximoRegional: str | None = None
    pracasRegionais: list[PracaRegionalDeralItem] = Field(default_factory=list)
    variantes: list[VariantePreco] = Field(default_factory=list)


class CatalogoMercadoResponse(BaseModel):
    """Resposta estruturada do catálogo dinâmico de commodities agropecuárias."""

    model_config = ConfigDict(extra="forbid")

    sucesso: bool = True
    versao: str = "1.0"
    dataConsultaIso: datetime
    cacheAtualizadoEmIso: datetime | None = None
    estadoDisponibilidade: Literal["NORMAL", "DEFASADO", "FONTE_INDISPONIVEL"] = "NORMAL"
    avisoLegal: str = AVISO_LEGAL_PRECOS
    totalItens: int
    itens: list[CommodityCatalogoItem] = Field(default_factory=list)


METADADOS_CATALOGO: list[dict[str, object]] = [
    {
        "id": "soja",
        "nome": "Soja em Grão",
        "categoria": "GRAOS_CEREAIS",
        "classificacaoAgronomica": "Leguminosa / Fabaceae (Glycine max)",
        "descricao": "Principal oleaginosa brasileira de exportação, balizada pela paridade nos portos e mercado físico regional.",
        "destaque": True,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "milho",
        "nome": "Milho Físico",
        "categoria": "GRAOS_CEREAIS",
        "classificacaoAgronomica": "Poácea (Gramínea) / Cereal (Zea mays)",
        "descricao": "Cereal base para alimentação animal e bioenergia, com forte liquidez nos mercados de safra e safrinha.",
        "destaque": True,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "trigo",
        "nome": "Trigo em Grão",
        "categoria": "GRAOS_CEREAIS",
        "classificacaoAgronomica": "Poácea (Gramínea) / Cereal de Inverno (Triticum aestivum)",
        "descricao": "Cereal nobre de inverno cultivado prioritariamente na Região Sul para abastecimento da indústria moageira nacional.",
        "destaque": False,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "arroz",
        "nome": "Arroz em Casca",
        "categoria": "GRAOS_CEREAIS",
        "classificacaoAgronomica": "Poácea (Gramínea) / Cereal Irrigado (Oryza sativa)",
        "descricao": "Arroz em casca irrigado recebido pelo produtor, alimento básico da dieta e balizador do complexo orizícola.",
        "destaque": False,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "aveia-branca",
        "nome": "Aveia Branca",
        "categoria": "GRAOS_CEREAIS",
        "classificacaoAgronomica": "Poácea (Gramínea) / Cereal de Inverno (Avena sativa)",
        "descricao": "Cereal de inverno de dupla aptidão para grãos e forragem animal, cultivado nas lavouras do Sul.",
        "destaque": False,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "canola",
        "nome": "Canola Grão",
        "categoria": "GRAOS_CEREAIS",
        "classificacaoAgronomica": "Crucífera / Brassicaceae (Brassica napus)",
        "descricao": "Oleaginosa de inverno rica em óleo vegetal nobre e matéria-prima para biocombustíveis.",
        "destaque": False,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "cevada",
        "nome": "Cevada em Grão",
        "categoria": "GRAOS_CEREAIS",
        "classificacaoAgronomica": "Poácea (Gramínea) / Cereal (Hordeum vulgare)",
        "descricao": "Cevada em grão recebida pelo produtor, conforme classificação comercial do DERAL.",
        "destaque": False,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "amendoim",
        "nome": "Amendoim em Casca",
        "categoria": "GRAOS_CEREAIS",
        "classificacaoAgronomica": "Leguminosa / Fabaceae (Arachis hypogaea)",
        "descricao": "Amendoim em casca comercializado pelo produtor rural, matéria-prima para confeitaria e indústria de óleos.",
        "destaque": False,
        "defaultUnidade": "Saca de 25 kg",
    },
    {
        "id": "cafe-arabica",
        "nome": "Café Beneficiado (Produtor)",
        "categoria": "CAFE",
        "classificacaoAgronomica": "Café beneficiado — classificação comercial DERAL",
        "descricao": "Café beneficiado recebido pelo produtor, sem identificação de espécie na publicação de origem.",
        "destaque": True,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "feijao",
        "nome": "Feijão de Cor",
        "categoria": "LEGUMINOSAS",
        "classificacaoAgronomica": "Leguminosa / Fabaceae (Phaseolus vulgaris)",
        "descricao": "Feijão de cor recebido pelo produtor, sem indicação de cultivar na publicação de origem.",
        "destaque": True,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "feijao-preto",
        "nome": "Feijão Preto",
        "categoria": "LEGUMINOSAS",
        "classificacaoAgronomica": "Leguminosa / Fabaceae (Phaseolus vulgaris)",
        "descricao": "Feijão comum tipo preto, com alta preferência na Região Sul e Sudeste, negociado em sacas de 60 kg.",
        "destaque": False,
        "defaultUnidade": "Saca de 60 kg",
    },
    {
        "id": "boi-gordo",
        "nome": "Boi Gordo",
        "categoria": "PECUARIA",
        "classificacaoAgronomica": "Bovinocultura de Corte / Ruminante (Bos taurus / Bos indicus)",
        "descricao": "Boi gordo terminado para abate, balizador da pecuária de corte e referência para a indústria frigorífica nacional.",
        "destaque": True,
        "defaultUnidade": "Arroba (@ de 15 kg)",
    },
    {
        "id": "boi-magro",
        "nome": "Boi Magro p/ Engorda",
        "categoria": "PECUARIA",
        "classificacaoAgronomica": "Bovinocultura de Corte / Categoria de Reposição",
        "descricao": "Boi magro destinado à engorda intensiva e confinamento, indicador chave do custo de reposição pecuária.",
        "destaque": False,
        "defaultUnidade": "Cabeça",
    },
    {
        "id": "vaca-em-pe",
        "nome": "Vaca em Pé (Abate)",
        "categoria": "PECUARIA",
        "classificacaoAgronomica": "Bovinocultura de Corte / Matrizes e Descarte",
        "descricao": "Vaca em pé para abate imediato, indicador do mercado de descarte pecuário e consumo de carne de fêmeas.",
        "destaque": False,
        "defaultUnidade": "Arroba (@ de 15 kg)",
    },
    {
        "id": "frango-vivo",
        "nome": "Frango Vivo",
        "categoria": "PECUARIA",
        "classificacaoAgronomica": "Avicultura de Corte (Gallus gallus domesticus)",
        "descricao": "Frango vivo no mercado independente da avicultura industrial, polo em que o Paraná lidera a produção brasileira.",
        "destaque": False,
        "defaultUnidade": "Quilo (kg)",
    },
    {
        "id": "suino",
        "nome": "Suíno Vivo",
        "categoria": "PECUARIA",
        "classificacaoAgronomica": "Suinocultura Industrial (Sus domesticus)",
        "descricao": "Suíno vivo terminado para abate na indústria frigorífica, com preço médio pago ao produtor independente.",
        "destaque": False,
        "defaultUnidade": "Quilo (kg)",
    },
    {
        "id": "leite",
        "nome": "Leite (Produtor)",
        "categoria": "PECUARIA",
        "classificacaoAgronomica": "Bovinocultura de Leite / Produto ao produtor",
        "descricao": "Leite recebido pelo produtor, sem qualificação de refrigeração na publicação de origem.",
        "destaque": False,
        "defaultUnidade": "Litro",
    },
    {
        "id": "ovo-grande",
        "nome": "Ovo Tipo Grande",
        "categoria": "PECUARIA",
        "classificacaoAgronomica": "Avicultura de Postura / Ovos Comerciais",
        "descricao": "Ovo tipo grande comercializado em caixas com 30 dúzias (360 ovos), referência da postura comercial.",
        "destaque": False,
        "defaultUnidade": "Caixa com 30 dúzias",
    },
    {
        "id": "cana-de-acucar",
        "nome": "Cana-de-Açúcar para Indústria",
        "categoria": "CANA_DERIVADOS",
        "classificacaoAgronomica": "Poácea (Gramínea) / Semi-perene (Saccharum officinarum)",
        "descricao": "Cana-de-açúcar destinada ao processamento agroindustrial de açúcar e etanol pelo setor sucroenergético.",
        "destaque": False,
        "defaultUnidade": "Tonelada (1.000 kg)",
    },
    {
        "id": "mandioca-industrial",
        "nome": "Mandioca Industrial",
        "categoria": "OUTROS",
        "classificacaoAgronomica": "Euforbiácea / Raiz Tuberosa (Manihot esculenta)",
        "descricao": "Mandioca industrial destinada a fecularias e indústrias de farinha, cultura de grande expressão no Paraná.",
        "destaque": False,
        "defaultUnidade": "Tonelada (1.000 kg)",
    },
    {
        "id": "erva-mate",
        "nome": "Erva-Mate Folha Verde",
        "categoria": "OUTROS",
        "classificacaoAgronomica": "Aquifoliácea / Cultura Nativa Florestal (Ilex paraguariensis)",
        "descricao": "Erva-mate folha verde entregue na indústria ervateira para beneficiamento de chimarrão e chás.",
        "destaque": False,
        "defaultUnidade": "Arroba (@ de 15 kg)",
    },
    {
        "id": "algodao",
        "nome": "Algodão em Pluma",
        "categoria": "FIBRAS",
        "classificacaoAgronomica": "Malvácea (Gossypium hirsutum L.)",
        "descricao": "Fibra têxtil de relevância global balizada pelo mercado spot e contratos de exportação.",
        "destaque": True,
        "defaultUnidade": "Arroba (@ de 15 kg)",
    },
]


_SNAPSHOT_CACHE_OVERRIDE: dict[str, object] | None = None


def set_snapshot_cache_override(snapshot_data: dict[str, object] | None) -> None:
    """Define ou limpa override do snapshot ativo para testes e sincronização em memória."""
    global _SNAPSHOT_CACHE_OVERRIDE
    _SNAPSHOT_CACHE_OVERRIDE = snapshot_data


def _carregar_snapshot() -> dict[str, object]:
    """Lê o snapshot oficial versionado do DERAL na memória dinâmica ou no filesystem."""
    if _SNAPSHOT_CACHE_OVERRIDE is not None:
        return _SNAPSHOT_CACHE_OVERRIDE
    try:
        from core.services.deral_snapshot_service import deral_snapshot_service
        active = deral_snapshot_service.get_cached_active_snapshot()
        if active is not None:
            return active
    except Exception:
        pass
    with SNAPSHOT_PATH.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _calcular_defasagem_dias(data_referencia_str: str, now: datetime) -> int:
    """Calcula defasagem em dias corridos entre a publicação e a consulta."""
    try:
        data_ref = datetime.fromisoformat(data_referencia_str).date()
        return max(0, (now.date() - data_ref).days)
    except (ValueError, TypeError):
        return 5


def _normalizar_item(
    item: dict[str, object], snapshot: dict[str, object], consulta: datetime
) -> PrecoPublicoItem:
    """Combina o registro original com a proveniência comum do documento."""
    documento = str(snapshot["documentoOficial"])
    # O documento identifica o fim do período de observação, não a data de publicação.
    data_ref = str(snapshot.get("dataReferencia") or snapshot["dataPublicacao"])
    defasagem = _calcular_defasagem_dias(data_ref, consulta)

    return PrecoPublicoItem.model_validate(
        {
            **item,
            "moeda": "BRL",
            "pracaReferencia": "Paraná — média semanal estadual",
            "fonteOficial": "Departamento de Economia Rural / SEAB-PR",
            "siglaFonte": "DERAL/SEAB-PR",
            "linkOficial": DERAL_PORTAL_URL,
            "urlConsultaInstitucional": DERAL_PORTAL_URL,
            "urlDocumentoDownload": documento,
            "dataReferencia": data_ref,
            "dataConsultaIso": consulta,
            "defasagemDiasAproximada": defasagem,
            "indicacaoTemporal": "Semanal — Preço Médio Produtor",
            "avisoLegal": AVISO_LEGAL_PRECOS,
            "documentoOficial": documento,
            "documentoHashSha256": snapshot["documentoHashSha256"],
            "dataPublicacao": None,
            "unidade": "Arroba" if item.get("unidadeOriginal") == "arroba" else item["unidade"],
            "transformacaoAplicada": snapshot["transformacaoAplicada"],
        }
    )


def carregar_precos_publicos(now: datetime | None = None) -> list[PrecoPublicoItem]:
    """Retorna somente registros com preço auditado presentes no snapshot oficial."""
    consulta = now or datetime.now(timezone.utc)
    snapshot = _carregar_snapshot()
    itens = snapshot.get("itens", [])
    if not isinstance(itens, list):
        return []
    ids = {item.get("id") for item in itens if isinstance(item, dict)}
    esperados = {str(meta["id"]) for meta in METADADOS_CATALOGO if meta["id"] != "algodao"}
    if len(itens) != 21 or ids != esperados:
        raise ValueError("Snapshot DERAL não contém os 21 preços homologados")
    return [_normalizar_item(item, snapshot, consulta) for item in itens if isinstance(item, dict)]


def _montar_item_catalogo(
    meta: dict[str, object],
    precos_map: dict[str, PrecoPublicoItem],
    snapshot: dict[str, object],
    max_defasagem_dias: int = MAX_PRECOS_SEMANAIS_FRESCOS_DIAS,
) -> CommodityCatalogoItem:
    """Monta um item do catálogo combinando metadados cadastrais e variantes reais."""
    cid = str(meta["id"])
    preco = precos_map.get(cid)
    categoria = meta["categoria"]  # type: ignore[assignment]
    classificacao_agro = str(meta["classificacaoAgronomica"])
    descricao = str(meta["descricao"])
    destaque = bool(meta.get("destaque", False))
    unidade = str(preco.unidade if preco else meta["defaultUnidade"])

    if preco:
        variante_deral = VariantePreco(
            varianteId=f"deral-pr-{cid}",
            siglaFonte="DERAL/SEAB-PR",
            fonteOficial="Departamento de Economia Rural / SEAB-PR",
            tipoPreco=preco.tipoPreco,
            pracaReferencia=preco.pracaReferencia,
            unidade=preco.unidade,
            moeda=preco.moeda,
            valor=preco.valor,
            valorOriginal=preco.valorOriginal,
            unidadeOriginal=preco.unidadeOriginal,
            dataReferencia=preco.dataReferencia,
            dataPublicacao=preco.dataPublicacao,
            defasagemDiasAproximada=preco.defasagemDiasAproximada,
            documentoOficial=preco.documentoOficial,
            documentoHashSha256=preco.documentoHashSha256,
            registroOriginal=preco.registroOriginal,
            estadoDisponibilidade=(
                "DISPONIVEL"
                if preco.defasagemDiasAproximada <= max_defasagem_dias
                else "DEFASADO"
            ),
            urlConsultaInstitucional=DERAL_PORTAL_URL,
            urlDocumentoDownload=DERAL_SPREADSHEET_URL,
            valorSemanaAnterior=preco.valorSemanaAnterior,
            variacaoSemanalAbsoluta=preco.variacaoSemanalAbsoluta,
            variacaoSemanalPct=preco.variacaoSemanalPct,
            valorMinimoRegional=preco.valorMinimoRegional,
            pracaMinimoRegional=preco.pracaMinimoRegional,
            valorMaximoRegional=preco.valorMaximoRegional,
            pracaMaximoRegional=preco.pracaMaximoRegional,
            pracasRegionais=preco.pracasRegionais,
        )
        return CommodityCatalogoItem(
            id=cid,
            nome=preco.commodityNome,
            categoria=categoria,
            classificacao=preco.classificacao,
            classificacaoAgronomica=classificacao_agro,
            descricao=descricao,
            destaque=destaque,
            tipoIndicador="FISICO_SPOT",
            pracaReferencia=preco.pracaReferencia,
            fontePrincipalNome="DERAL/SEAB-PR",
            siglaFonte=preco.siglaFonte,
            urlConsultaInstitucional=DERAL_PORTAL_URL,
            urlDocumentoDownload=DERAL_SPREADSHEET_URL,
            valor=preco.valor,
            moeda=preco.moeda,
            unidade=preco.unidade,
            dataReferencia=preco.dataReferencia,
            dataPublicacao=preco.dataPublicacao,
            defasagemDiasAproximada=preco.defasagemDiasAproximada,
            documentoOficial=preco.documentoOficial,
            documentoHashSha256=preco.documentoHashSha256,
            registroOriginal=preco.registroOriginal,
            estadoDisponibilidade=variante_deral.estadoDisponibilidade,
            valorSemanaAnterior=preco.valorSemanaAnterior,
            variacaoSemanalAbsoluta=preco.variacaoSemanalAbsoluta,
            variacaoSemanalPct=preco.variacaoSemanalPct,
            valorMinimoRegional=preco.valorMinimoRegional,
            pracaMinimoRegional=preco.pracaMinimoRegional,
            valorMaximoRegional=preco.valorMaximoRegional,
            pracaMaximoRegional=preco.pracaMaximoRegional,
            pracasRegionais=preco.pracasRegionais,
            variantes=[variante_deral],
        )

    # Item referenciado sem cotação aberta nesta fase (ex: Algodão)
    variante_conab = VariantePreco(
        varianteId=f"conab-nacional-{cid}",
        siglaFonte="CONAB/MAPA",
        fonteOficial="Companhia Nacional de Abastecimento",
        tipoPreco="REFERENCIA_OFICIAL_GOVERNAMENTAL",
        pracaReferencia="Brasil — Referência Nacional",
        unidade=unidade,
        moeda="BRL",
        valor=None,
        estadoDisponibilidade="LINK_HOMOLOGADO",
        urlConsultaInstitucional="https://www.gov.br/conab/pt-br/assuntos/informacoes-agropecuarias/precos-agropecuarios",
        urlDocumentoDownload=None,
    )
    return CommodityCatalogoItem(
        id=cid,
        nome=str(meta["nome"]),
        categoria=categoria,
        classificacao=f"{meta['nome']} — Referência Institucional Governamental",
        classificacaoAgronomica=classificacao_agro,
        descricao=descricao,
        destaque=destaque,
        tipoIndicador="FISICO_SPOT",
        pracaReferencia="Brasil — Referência Nacional",
        fontePrincipalNome="CONAB / MAPA",
        siglaFonte="CONAB/MAPA",
        urlConsultaInstitucional="https://www.gov.br/conab/pt-br/assuntos/informacoes-agropecuarias/precos-agropecuarios",
        urlDocumentoDownload=None,
        valor=None,
        moeda="BRL",
        unidade=unidade,
        dataReferencia=None,
        dataPublicacao=None,
        defasagemDiasAproximada=None,
        documentoOficial=None,
        documentoHashSha256=None,
        registroOriginal=None,
        estadoDisponibilidade="LINK_HOMOLOGADO",
        variantes=[variante_conab],
    )


def carregar_catalogo_mercado(
    now: datetime | None = None,
    max_defasagem_dias: int = MAX_PRECOS_SEMANAIS_FRESCOS_DIAS,
) -> CatalogoMercadoResponse:
    """Gera resposta completa do catálogo com dados cadastrais e preços homologados."""
    consulta = now or datetime.now(timezone.utc)
    precos_itens = carregar_precos_publicos(consulta)
    precos_map = {item.id: item for item in precos_itens}
    snapshot = _carregar_snapshot()

    itens = [
        _montar_item_catalogo(meta, precos_map, snapshot, max_defasagem_dias)
        for meta in METADADOS_CATALOGO
    ]
    estado_catalogo = (
        "FONTE_INDISPONIVEL"
        if not precos_itens
        else "DEFASADO"
        if any(item.defasagemDiasAproximada > max_defasagem_dias for item in precos_itens)
        else "NORMAL"
    )

    return CatalogoMercadoResponse(
        sucesso=True,
        versao="1.0",
        dataConsultaIso=consulta,
        cacheAtualizadoEmIso=consulta,
        estadoDisponibilidade=estado_catalogo,
        avisoLegal=AVISO_LEGAL_PRECOS,
        totalItens=len(itens),
        itens=itens,
    )


PRECOS_OFICIAIS_HOMOLOGADOS = _carregar_snapshot()["itens"]

