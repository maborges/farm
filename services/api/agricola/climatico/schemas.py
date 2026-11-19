import math
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

VARIAVEIS_CLIMATICAS_FITOSSANITARIAS = frozenset({
    "temp_media_c",
    "temp_max_c",
    "temp_min_c",
    "umidade_rel_pct",
    "precipitacao_mm",
})
OPERADORES_FITOSSANITARIOS = frozenset({">=", "<=", ">", "<", "between"})


def _numero_finito(valor: object) -> bool:
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return False
    try:
        return math.isfinite(float(valor))
    except (OverflowError, ValueError):
        return False


def _limite_variavel_valido(variavel: str, valor: int | float) -> bool:
    if variavel == "umidade_rel_pct":
        return 0 <= valor <= 100
    if variavel == "precipitacao_mm":
        return valor >= 0
    if variavel.startswith("temp_"):
        return -90 <= valor <= 60
    return True


def validar_regras_fitossanitarias(regras: dict) -> dict:
    """Valida estrutura mecânica do JSON; não valida eficácia agronômica."""
    if not isinstance(regras, dict):
        raise ValueError("regras_risco deve ser um objeto JSON")

    condicoes = regras.get("condicoes")
    if not isinstance(condicoes, list) or not condicoes:
        raise ValueError("regras_risco.condicoes deve conter ao menos uma condição")

    peso_total = 0.0
    for indice, condicao in enumerate(condicoes):
        prefixo = f"condicoes[{indice}]"
        if not isinstance(condicao, dict):
            raise ValueError(f"{prefixo} deve ser um objeto")

        variavel = condicao.get("variavel")
        if variavel not in VARIAVEIS_CLIMATICAS_FITOSSANITARIAS:
            raise ValueError(f"{prefixo}.variavel não é suportada")

        operador = condicao.get("operador")
        if operador not in OPERADORES_FITOSSANITARIOS:
            raise ValueError(f"{prefixo}.operador não é suportado")

        peso = condicao.get("peso", 1)
        if not _numero_finito(peso) or peso <= 0:
            raise ValueError(f"{prefixo}.peso deve ser numérico, finito e positivo")
        peso_total += float(peso)
        if not math.isfinite(peso_total):
            raise ValueError("a soma dos pesos deve ser finita")

        if operador == "between":
            limites = (condicao.get("min"), condicao.get("max"))
            if any(
                not _numero_finito(limite)
                for limite in limites
            ):
                raise ValueError(f"{prefixo}.min e .max devem ser numéricos e finitos")
            if limites[0] > limites[1]:
                raise ValueError(f"{prefixo}.min não pode ser maior que .max")
            if any(not _limite_variavel_valido(variavel, limite) for limite in limites):
                raise ValueError(f"{prefixo} possui limites fora do domínio da variável")
        else:
            valor = condicao.get("valor")
            if not _numero_finito(valor):
                raise ValueError(f"{prefixo}.valor deve ser numérico e finito")
            if not _limite_variavel_valido(variavel, valor):
                raise ValueError(f"{prefixo}.valor está fora do domínio da variável")

    niveis = {
        "nivel_medio_pct": regras.get("nivel_medio_pct", 35),
        "nivel_alto_pct": regras.get("nivel_alto_pct", 60),
        "nivel_critico_pct": regras.get("nivel_critico_pct", 80),
    }
    for nome, valor in niveis.items():
        if not _numero_finito(valor):
            raise ValueError(f"{nome} deve ser numérico e finito")
        if not 0 <= valor <= 100:
            raise ValueError(f"{nome} deve estar entre 0 e 100")
    if not (niveis["nivel_medio_pct"] <= niveis["nivel_alto_pct"] <= niveis["nivel_critico_pct"]):
        raise ValueError("limiares devem obedecer medio <= alto <= critico")

    if "metadados" in regras and regras["metadados"] is not None:
        metadados = regras["metadados"]
        if not isinstance(metadados, dict):
            raise ValueError("regras_risco.metadados deve ser um objeto JSON")
        if "fonte_url" in metadados and metadados["fonte_url"] is not None:
            fonte_url = metadados["fonte_url"]
            if not isinstance(fonte_url, str) or (
                fonte_url != "" and not fonte_url.startswith(("https://", "http://"))
            ):
                raise ValueError(
                    "regras_risco.metadados.fonte_url deve usar protocolo http:// ou https://"
                )

    return regras


class ClimaResponse(BaseModel):
    id: UUID
    unidade_produtiva_id: UUID
    data_registro: date
    precipitacao_mm: float | None
    temp_max_c: float | None
    temp_min_c: float | None
    temp_media_c: float | None
    umidade_rel_pct: float | None
    evapotranspiracao_mm: float | None
    gdu_calculado: float | None
    vento_kmh: float | None = None
    fonte: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClimaResumoResponse(BaseModel):
    unidade_produtiva_id: UUID
    data_registro: date | None = None
    temperatura_atual: float | None = None
    temperatura_min: float | None = None
    temperatura_max: float | None = None
    umidade: float | None = None
    precipitacao_mm: float | None = None
    vento_kmh: float | None = None
    condicao: str | None = None
    fonte: str | None = None
    status_operacional: str
    alertas_ativos: int = 0

    model_config = ConfigDict(from_attributes=True)


class ClimaAlertaResponse(BaseModel):
    id: UUID
    severity: str
    priority: str
    title: str
    description: str
    source_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecomendacaoOperacionalResponse(BaseModel):
    unidade_produtiva_id: UUID
    tipo_operacao: str
    status: str
    severidade: str
    motivo: str
    dados_utilizados: dict
    data_referencia: datetime
    fonte: str
    validade_horas: int

    model_config = ConfigDict(from_attributes=True)

class PrevisaoClimaResponse(BaseModel):
    id: UUID
    unidade_produtiva_id: UUID
    data_previsao: date
    precipitacao_mm: float | None = None
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    probabilidade_chuva_pct: float | None = None
    periodos: list[dict] = Field(default_factory=list)
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class SerieTemporalClima(BaseModel):
    data: date
    temp_min: float | None = None
    temp_max: float | None = None
    temp_media: float | None = None
    precipitacao: float | None = None


class RiscoClimatico(BaseModel):
    tipo: str
    nivel: str  # ex: BAIXO, MEDIO, ALTO, CRITICO
    mensagem: str
    data_alerta: date | None = None


class RiscoDoencaResponse(BaseModel):
    """Pontuação heurística de favorabilidade climática, não diagnóstico/probabilidade."""
    doenca: str
    cultura: str
    nivel_favorabilidade: Literal["baixa", "moderada", "alta", "muito_alta"]
    favorabilidade_pct: int = Field(ge=0, le=100)
    nivel: str = Field(
        deprecated=True,
        description="Alias legado de nivel_favorabilidade; não representa severidade da doença.",
    )
    probabilidade_pct: int = Field(
        deprecated=True,
        description="Alias legado de favorabilidade_pct; não é probabilidade epidemiológica.",
    )
    auto_copied: bool = False


class AgriculturaInteligenciaResponse(BaseModel):
    """Campos de inteligência agronômica focados em agricultura."""
    janela_pulverizacao: list[dict] = Field(default_factory=list)
    balanco_hidrico: list[dict] = Field(default_factory=list)
    risco_doencas: list[RiscoDoencaResponse] = Field(default_factory=list)


class ClimaInteligenciaResponse(BaseModel):
    gdu_acumulado: float
    gdu_progresso_pct: float | None = None
    riscos: list[RiscoClimatico]
    historico: list[SerieTemporalClima]
    agricultura: AgriculturaInteligenciaResponse | None = None
    risco_fitossanitario_status: Literal[
        "SEM_CULTURA_ATIVA",
        "SEM_MODELO_APLICAVEL",
        "DADOS_CLIMATICOS_INSUFICIENTES",
        "DADOS_CLIMATICOS_INVALIDOS",
        "CONFIGURACAO_INVALIDA",
        "PARCIAL",
        "CALCULADO",
    ] = "DADOS_CLIMATICOS_INSUFICIENTES"

    model_config = ConfigDict(from_attributes=True)


class ModeloFitossanitarioBase(BaseModel):
    cultura: str
    doenca: str
    regras_risco: dict


class ModeloFitossanitarioCreate(ModeloFitossanitarioBase):
    @field_validator("regras_risco")
    @classmethod
    def validar_json_fitossanitario(cls, value: dict) -> dict:
        return validar_regras_fitossanitarias(value)


class ModeloFitossanitarioUpdate(BaseModel):
    cultura: str | None = None
    doenca: str | None = None
    regras_risco: dict | None = None

    @field_validator("regras_risco")
    @classmethod
    def validar_json_fitossanitario(cls, value: dict | None) -> dict | None:
        return validar_regras_fitossanitarias(value) if value is not None else None


class ModeloFitossanitarioResponse(ModeloFitossanitarioBase):
    id: UUID
    is_global: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
