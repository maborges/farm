"""Cliente, lista permitida e contratos para as estatísticas oficiais do IBGE/SIDRA (PAM, LSPA, PPM).

Nenhuma URL é montada a partir de texto livre do usuário: apenas inteiros e
identificadores presentes nas listas permitidas deste módulo compõem a consulta.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

SIDRA_VALUES_URL = "https://apisidra.ibge.gov.br/values"
IBGE_AGREGADOS_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"
IBGE_LOCALIDADES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
SIDRA_TABLE_URL = "https://sidra.ibge.gov.br/tabela"
MAX_RESPONSE_BYTES = 2_000_000
ANO_MINIMO = 1974

AVISO_ESTATISTICA = (
    "Estatística oficial de produção divulgada pelo IBGE (SIDRA). "
    "Não é cotação nem preço de comercialização."
)
AVISO_ESTIMATIVA = (
    "Estimativa mensal do LSPA/IBGE, sujeita a revisão a cada divulgação. "
    "Não é cotação nem preço de comercialização."
)

Nivel = Literal["BRASIL", "UF", "MUNICIPIO"]
Tipo = Literal["LAVOURA", "REBANHO", "PRODUCAO_ANIMAL"]
Fonte = Literal["PAM", "PPM", "LSPA"]
Estado = Literal["NORMAL", "FONTE_INDISPONIVEL", "SEM_DADOS", "INDISPONIVEL"]

NIVEL_SIDRA: dict[str, str] = {"BRASIL": "1", "UF": "3", "MUNICIPIO": "6"}


@dataclass(frozen=True)
class VariavelSidra:
    """Variável SIDRA permitida, com unidade oficial esperada na resposta."""

    codigo: int
    id: str
    nome: str
    unidade: str


@dataclass(frozen=True)
class FonteSidra:
    """Tabela SIDRA homologada com variáveis e classificação permitidas."""

    fonte: Fonte
    pesquisa: str
    tabela: int
    classificacao: int
    variaveis: tuple[VariavelSidra, ...]
    periodicidade: Literal["ANUAL", "MENSAL"]


@dataclass(frozen=True)
class ProdutoSidra:
    """Produto/atividade do catálogo com os códigos de categoria por tabela."""

    id: str
    nome: str
    tipo: Tipo
    fonte: FonteSidra
    categoria: int
    unidade_override: str | None = None
    lspa_categorias: tuple[int, ...] = ()


_PAM_VARS = (
    VariavelSidra(8331, "AREA_PLANTADA", "Área plantada ou destinada à colheita", "Hectares"),
    VariavelSidra(216, "AREA_COLHIDA", "Área colhida", "Hectares"),
    VariavelSidra(214, "PRODUCAO", "Quantidade produzida", "Toneladas"),
    VariavelSidra(
        215, "VALOR_PRODUCAO", "Valor da produção", "Mil Reais"
    ),
    VariavelSidra(112, "RENDIMENTO_MEDIO", "Rendimento médio da produção", "Quilogramas por Hectare"),
)
_LSPA_VARS = (
    VariavelSidra(109, "AREA_PLANTADA", "Área plantada", "Hectares"),
    VariavelSidra(216, "AREA_COLHIDA", "Área colhida", "Hectares"),
    VariavelSidra(35, "PRODUCAO", "Produção", "Toneladas"),
    VariavelSidra(36, "RENDIMENTO_MEDIO", "Rendimento médio", "Quilogramas por Hectare"),
)

FONTE_PAM = FonteSidra(
    "PAM", "Produção Agrícola Municipal (PAM)", 5457, 782, _PAM_VARS, "ANUAL"
)
FONTE_LSPA = FonteSidra(
    "LSPA", "Levantamento Sistemático da Produção Agrícola (LSPA)", 6588, 48, _LSPA_VARS, "MENSAL"
)
FONTE_PPM_REBANHO = FonteSidra(
    "PPM",
    "Pesquisa da Pecuária Municipal (PPM) — Efetivo dos rebanhos",
    3939,
    79,
    (VariavelSidra(105, "EFETIVO_REBANHO", "Efetivo dos rebanhos", "Cabeças"),),
    "ANUAL",
)
FONTE_PPM_PRODUCAO = FonteSidra(
    "PPM",
    "Pesquisa da Pecuária Municipal (PPM) — Produção de origem animal",
    74,
    80,
    (VariavelSidra(106, "PRODUCAO_ANIMAL", "Produção de origem animal", ""),),
    "ANUAL",
)


def _lavoura(slug: str, nome: str, pam: int, lspa: tuple[int, ...] = ()) -> ProdutoSidra:
    return ProdutoSidra(slug, nome, "LAVOURA", FONTE_PAM, pam, None, lspa)


def _rebanho(slug: str, nome: str, cat: int) -> ProdutoSidra:
    return ProdutoSidra(slug, nome, "REBANHO", FONTE_PPM_REBANHO, cat)


def _origem_animal(slug: str, nome: str, cat: int, unidade: str) -> ProdutoSidra:
    return ProdutoSidra(slug, nome, "PRODUCAO_ANIMAL", FONTE_PPM_PRODUCAO, cat, unidade)


PRODUTOS: dict[str, ProdutoSidra] = {
    p.id: p
    for p in (
        _lavoura("soja", "Soja (em grão)", 40124, (39443,)),
        _lavoura("milho", "Milho (em grão)", 40122, (39441, 39442)),
        _lavoura("cafe", "Café (em grão) — total", 40139, (40527,)),
        _lavoura("pimenta-do-reino", "Pimenta-do-reino", 40269),
        _lavoura("cana-de-acucar", "Cana-de-açúcar", 40106, (39456,)),
        _lavoura("trigo", "Trigo (em grão)", 40127, (39445,)),
        _lavoura("arroz", "Arroz (em casca)", 40102, (39432,)),
        _lavoura("feijao", "Feijão (em grão)", 40112, (39436, 39437, 39438)),
        _lavoura("algodao", "Algodão herbáceo (em caroço)", 40099, (39429,)),
        _lavoura("sorgo", "Sorgo (em grão)", 40125, (39444,)),
        _lavoura("laranja", "Laranja", 40151, (39463,)),
        _lavoura("cacau", "Cacau (em amêndoa)", 40138, (39453,)),
        _lavoura("banana", "Banana (cacho)", 40136, (39449,)),
        _lavoura("mandioca", "Mandioca", 40119),
        _rebanho("bovinos", "Bovinos", 2670),
        _rebanho("suinos", "Suínos (total)", 32794),
        _rebanho("galinaceos", "Galináceos (total)", 32796),
        _rebanho("ovinos", "Ovinos", 2677),
        _rebanho("caprinos", "Caprinos", 2681),
        _rebanho("bubalinos", "Bubalinos", 2675),
        _rebanho("equinos", "Equinos", 2672),
        _origem_animal("leite", "Leite", 2682, "Mil litros"),
        _origem_animal("ovos-galinha", "Ovos de galinha", 2685, "Mil dúzias"),
        _origem_animal("mel", "Mel de abelha", 2687, "Quilogramas"),
    )
}

UFS: dict[str, tuple[str, str]] = {
    "11": ("RO", "Rondônia"), "12": ("AC", "Acre"), "13": ("AM", "Amazonas"),
    "14": ("RR", "Roraima"), "15": ("PA", "Pará"), "16": ("AP", "Amapá"),
    "17": ("TO", "Tocantins"), "21": ("MA", "Maranhão"), "22": ("PI", "Piauí"),
    "23": ("CE", "Ceará"), "24": ("RN", "Rio Grande do Norte"), "25": ("PB", "Paraíba"),
    "26": ("PE", "Pernambuco"), "27": ("AL", "Alagoas"), "28": ("SE", "Sergipe"),
    "29": ("BA", "Bahia"), "31": ("MG", "Minas Gerais"), "32": ("ES", "Espírito Santo"),
    "33": ("RJ", "Rio de Janeiro"), "35": ("SP", "São Paulo"), "41": ("PR", "Paraná"),
    "42": ("SC", "Santa Catarina"), "43": ("RS", "Rio Grande do Sul"),
    "50": ("MS", "Mato Grosso do Sul"), "51": ("MT", "Mato Grosso"),
    "52": ("GO", "Goiás"), "53": ("DF", "Distrito Federal"),
}


class RespostaIbgeBase(BaseModel):
    """Campos comuns de disponibilidade de todas as respostas IBGE."""

    model_config = ConfigDict(extra="forbid")

    sucesso: bool
    versao: str = "1.0"
    fonteOficial: str = "Instituto Brasileiro de Geografia e Estatística (IBGE) — SIDRA"
    dataConsultaIso: datetime
    cacheAtualizadoEmIso: datetime | None = None
    estadoDisponibilidade: Estado
    estaDesatualizado: bool
    avisoLegal: str = AVISO_ESTATISTICA


class LocalidadeIbge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nivel: Nivel
    codigo: str
    nome: str


class PontoSerieIbge(BaseModel):
    """Observação oficial; `valor` nulo indica dado não disponível/inibido pelo IBGE."""

    model_config = ConfigDict(extra="forbid")

    periodo: str
    valor: float | None = Field(default=None, allow_inf_nan=False)
    simboloIbge: str | None = None


class IndicadorIbge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nomeOficial: str
    codigoVariavelSidra: int
    recorte: str | None = None
    unidade: str
    pontos: list[PontoSerieIbge]
    ultimoPeriodo: str | None = None
    ultimoValor: float | None = None


class ProdutoIbge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    tipo: Tipo


class EstatisticasIbgeResponse(RespostaIbgeBase):
    """Contrato das consultas PAM, PPM e LSPA."""

    pesquisa: str
    fontePesquisa: Fonte
    tabelaSidra: int
    urlTabela: str
    periodicidade: Literal["ANUAL", "MENSAL"]
    produto: ProdutoIbge
    localidade: LocalidadeIbge
    periodoSolicitado: str
    ultimoPeriodoDisponivel: str | None = None
    dataAtualizacaoFonte: date | None = None
    avisoDefasagem: str | None = None
    indicadores: list[IndicadorIbge]


class MunicipioIbge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    nome: str


class MunicipiosIbgeResponse(RespostaIbgeBase):
    uf: str
    avisoLegal: str = "Lista oficial de municípios (IBGE Localidades)."
    itens: list[MunicipioIbge]


class ProdutoCatalogoIbge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    tipo: Tipo
    pesquisa: str
    indicadores: list[str]
    suportaLspa: bool


class UfIbge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    sigla: str
    nome: str


class CatalogoIbgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    versao: str = "1.0"
    anoMinimo: int = ANO_MINIMO
    produtos: list[ProdutoCatalogoIbge]
    ufs: list[UfIbge]


@dataclass(frozen=True)
class ConsultaSidra:
    """Consulta validada contra as listas permitidas."""

    produto: ProdutoSidra
    fonte: FonteSidra
    nivel: Nivel
    codigo: str
    periodo: str
    categorias: tuple[int, ...]


_SYMBOLS_NULL = {"...", "X", ".."}
_RE_PERIODO = re.compile(r"^(\d{4})(\d{2})?$")
_RE_NUMERACAO = re.compile(r"^\d+(\.\d+)*\s+")


def montar_url_valores(consulta: ConsultaSidra) -> str:
    """Monta a URL SIDRA exclusivamente com inteiros e códigos da lista permitida.

    Args:
        consulta: Consulta já validada.

    Returns:
        URL absoluta do endpoint `values` do SIDRA.
    """
    fonte = consulta.fonte
    variaveis = ",".join(str(v.codigo) for v in fonte.variaveis)
    categorias = ",".join(str(c) for c in consulta.categorias)
    nivel = NIVEL_SIDRA[consulta.nivel]
    local = "all" if consulta.nivel == "BRASIL" else consulta.codigo
    periodo = consulta.periodo.replace(" ", "%20")
    return (
        f"{SIDRA_VALUES_URL}/t/{fonte.tabela}/n{nivel}/{local}/v/{variaveis}"
        f"/p/{periodo}/c{fonte.classificacao}/{categorias}?formato=json"
    )


def parse_valor_sidra(raw: object) -> tuple[float | None, str | None]:
    """Converte o campo `V` do SIDRA.

    Args:
        raw: Valor bruto retornado.

    Returns:
        Tupla (valor, símbolo). `-` é zero absoluto; `...` e `X` são dado ausente.

    Raises:
        ValueError: Valor não numérico e fora dos símbolos oficiais.
    """
    text = str(raw).strip()
    if text == "-":
        return 0.0, "-"
    if text in _SYMBOLS_NULL:
        return None, text
    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(f"Valor SIDRA não numérico: {text!r}") from exc
    if not math.isfinite(number):
        raise ValueError("Valor SIDRA não finito")
    return number, None


def normalizar_periodo(code: str) -> str:
    """Normaliza 'YYYY' ou 'YYYYMM' para 'YYYY' ou 'YYYY-MM'.

    Raises:
        ValueError: Código de período fora do padrão.
    """
    match = _RE_PERIODO.match(code)
    if not match:
        raise ValueError(f"Período SIDRA inválido: {code!r}")
    year, month = match.group(1), match.group(2)
    return f"{year}-{month}" if month else year


def _expected_unit(variavel: VariavelSidra, consulta: ConsultaSidra) -> str:
    return consulta.produto.unidade_override or variavel.unidade


def _validar_linha(row: object, consulta: ConsultaSidra, vars_by_code: dict[str, VariavelSidra]) -> dict[str, str]:
    if not isinstance(row, dict):
        raise ValueError("Linha SIDRA inválida")
    campos = {k: row.get(k) for k in ("MN", "V", "D1C", "D1N", "D2C", "D3C", "D4C", "D4N")}
    if any(not isinstance(v, str) for v in campos.values()):
        raise ValueError("Campos obrigatórios ausentes na linha SIDRA")
    esperado = "1" if consulta.nivel == "BRASIL" else consulta.codigo
    if campos["D1C"] != esperado:
        raise ValueError("Localidade retornada difere da solicitada")
    variavel = vars_by_code.get(campos["D2C"] or "")
    if variavel is None:
        raise ValueError("Variável fora da lista permitida")
    if campos["MN"] != _expected_unit(variavel, consulta):
        raise ValueError("Unidade de medida divergente da homologada")
    if campos["D4C"] not in {str(c) for c in consulta.categorias}:
        raise ValueError("Categoria fora da lista permitida")
    return {k: str(v) for k, v in campos.items()}


def parse_resposta_sidra(
    payload: object, consulta: ConsultaSidra
) -> tuple[str | None, list[IndicadorIbge]]:
    """Valida e converte a resposta do SIDRA em indicadores.

    Args:
        payload: JSON decodificado do SIDRA (cabeçalho + linhas).
        consulta: Consulta executada.

    Returns:
        Nome da localidade (ou None sem dados) e lista de indicadores.

    Raises:
        ValueError: Estrutura, unidade, localidade ou valores inválidos.
    """
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise ValueError("Resposta SIDRA fora do formato esperado")
    rows = payload[1:]
    vars_by_code = {str(v.codigo): v for v in consulta.fonte.variaveis}
    grupos: dict[tuple[str, str], list[PontoSerieIbge]] = {}
    nomes: dict[str, str] = {}
    local_nome: str | None = None
    for row in rows:
        c = _validar_linha(row, consulta, vars_by_code)
        valor, simbolo = parse_valor_sidra(c["V"])
        ponto = PontoSerieIbge(periodo=normalizar_periodo(c["D3C"]), valor=valor, simboloIbge=simbolo)
        grupos.setdefault((c["D2C"], c["D4C"]), []).append(ponto)
        nomes[c["D4C"]] = _RE_NUMERACAO.sub("", c["D4N"])
        local_nome = c["D1N"]
    return local_nome, _montar_indicadores(grupos, nomes, consulta, vars_by_code)


def _montar_indicadores(
    grupos: dict[tuple[str, str], list[PontoSerieIbge]],
    nomes: dict[str, str],
    consulta: ConsultaSidra,
    vars_by_code: dict[str, VariavelSidra],
) -> list[IndicadorIbge]:
    ordem = {str(v.codigo): i for i, v in enumerate(consulta.fonte.variaveis)}
    indicadores: list[IndicadorIbge] = []
    for (var_code, cat_code), pontos in sorted(grupos.items(), key=lambda kv: (kv[0][1], ordem[kv[0][0]])):
        variavel = vars_by_code[var_code]
        pontos.sort(key=lambda p: p.periodo)
        validos = [p for p in pontos if p.valor is not None]
        ultimo = validos[-1] if validos else None
        indicadores.append(
            IndicadorIbge(
                id=variavel.id,
                nomeOficial=variavel.nome,
                codigoVariavelSidra=variavel.codigo,
                recorte=nomes[cat_code] if len(consulta.categorias) > 1 else None,
                unidade=_expected_unit(variavel, consulta),
                pontos=pontos,
                ultimoPeriodo=ultimo.periodo if ultimo else None,
                ultimoValor=ultimo.valor if ultimo else None,
            )
        )
    return indicadores


def url_tabela(tabela: int) -> str:
    """URL pública da tabela no portal SIDRA."""
    return f"{SIDRA_TABLE_URL}/{tabela}"


def parse_modificacoes(payload: object) -> dict[str, date]:
    """Extrai a data de modificação por período da API de agregados (melhor esforço).

    Args:
        payload: JSON de `/agregados/{tabela}/periodos`.

    Returns:
        Mapa período normalizado -> data de modificação (ignora 01/01/0001).
    """
    if not isinstance(payload, list):
        return {}
    resultado: dict[str, date] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            periodo = normalizar_periodo(str(item["id"]))
            dia, mes, ano = (int(p) for p in str(item["modificacao"]).split("/"))
            if ano > 1900:
                resultado[periodo] = date(ano, mes, dia)
        except (KeyError, ValueError):
            continue
    return resultado


class IbgeSidraClient:
    """Cliente assíncrono do SIDRA com timeout, limite de tamanho e sem redirecionamentos."""

    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 10.0) -> None:
        self.client = client
        self.timeout = timeout

    async def _get_json(self, url: str) -> object:
        """GET restrito às URLs montadas por este módulo.

        Raises:
            httpx.HTTPError: Falha de rede, timeout ou status não 2xx.
            ValueError: Corpo grande demais ou JSON malformado.
        """
        headers = {"Accept": "application/json", "User-Agent": "DeepFarms-Agro-Client/1.0"}
        if self.client is not None:
            response = await self.client.get(url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as http:
                response = await http.get(url, headers=headers)
        response.raise_for_status()
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ValueError("Resposta do IBGE excede o limite permitido")
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise ValueError("JSON do IBGE malformado") from exc

    async def fetch_valores(self, consulta: ConsultaSidra) -> tuple[str | None, list[IndicadorIbge]]:
        """Consulta e valida os valores SIDRA.

        Raises:
            httpx.HTTPError: Falha de transporte/status.
            ValueError: Resposta inválida.
        """
        payload = await self._get_json(montar_url_valores(consulta))
        return parse_resposta_sidra(payload, consulta)

    async def fetch_modificacoes(self, tabela: int) -> dict[str, date]:
        """Obtém datas de atualização por período; qualquer falha resulta em mapa vazio."""
        try:
            payload = await self._get_json(f"{IBGE_AGREGADOS_URL}/{tabela}/periodos")
        except (httpx.HTTPError, ValueError, asyncio.TimeoutError):
            return {}
        return parse_modificacoes(payload)

    async def fetch_municipios(self, uf: str) -> list[MunicipioIbge]:
        """Lista municípios de uma UF da lista permitida.

        Raises:
            ValueError: UF fora da lista permitida ou resposta inválida.
            httpx.HTTPError: Falha de transporte/status.
        """
        if uf not in UFS:
            raise ValueError("UF fora da lista permitida")
        payload = await self._get_json(f"{IBGE_LOCALIDADES_URL}/{uf}/municipios")
        if not isinstance(payload, list):
            raise ValueError("Lista de municípios inválida")
        itens: list[MunicipioIbge] = []
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("nome"), str):
                codigo = str(item.get("id", ""))
                if re.fullmatch(r"\d{7}", codigo) and codigo.startswith(uf):
                    itens.append(MunicipioIbge(codigo=codigo, nome=item["nome"]))
        if not itens:
            raise ValueError("Nenhum município válido retornado")
        return sorted(itens, key=lambda m: m.nome)
