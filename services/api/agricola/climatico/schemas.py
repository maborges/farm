from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    """Risco fitossanitário calculado pelo motor de inteligência para uma cultura ativa."""
    doenca: str
    cultura: str
    nivel: str  # baixo, medio, alto, critico
    probabilidade_pct: int
    auto_copied: bool = False


class AgriculturaInteligenciaResponse(BaseModel):
    """Campos de inteligência agronômica focados em agricultura."""
    risco_doencas: list[RiscoDoencaResponse] = []


class ClimaInteligenciaResponse(BaseModel):
    gdu_acumulado: float
    gdu_progresso_pct: float | None = None
    riscos: list[RiscoClimatico]
    historico: list[SerieTemporalClima]
    agricultura: AgriculturaInteligenciaResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ModeloFitossanitarioBase(BaseModel):
    cultura: str
    doenca: str
    regras_risco: dict


class ModeloFitossanitarioCreate(ModeloFitossanitarioBase):
    pass


class ModeloFitossanitarioUpdate(BaseModel):
    cultura: str | None = None
    doenca: str | None = None
    regras_risco: dict | None = None


class ModeloFitossanitarioResponse(ModeloFitossanitarioBase):
    id: UUID
    is_global: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
