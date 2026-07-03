from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
