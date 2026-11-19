from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NDVICreate(BaseModel):
    talhao_id: UUID
    data_captura: date
    cobertura_nuvens_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    indice_medio: float | None = Field(default=None, ge=-1.0, le=1.0)
    indice_minimo: float | None = Field(default=None, ge=-1.0, le=1.0)
    indice_maximo: float | None = Field(default=None, ge=-1.0, le=1.0)
    url_imagem_colorida: str | None = None
    url_raw_data: str | None = None
    satelite: str = "Sentinel-2"

    @model_validator(mode="after")
    def validar_intervalo_indices(self) -> NDVICreate:
        if (
            self.indice_minimo is not None
            and self.indice_maximo is not None
            and self.indice_minimo > self.indice_maximo
        ):
            raise ValueError("NDVI mínimo não pode ser maior que o NDVI máximo.")
        if (
            self.indice_minimo is not None
            and self.indice_medio is not None
            and self.indice_medio < self.indice_minimo
        ):
            raise ValueError("NDVI médio não pode ser menor que o NDVI mínimo.")
        if (
            self.indice_maximo is not None
            and self.indice_medio is not None
            and self.indice_medio > self.indice_maximo
        ):
            raise ValueError("NDVI médio não pode ser maior que o NDVI máximo.")
        return self


class NDVIResponse(BaseModel):
    id: UUID
    talhao_id: UUID
    data_captura: date
    cobertura_nuvens_pct: float | None
    indice_medio: float | None
    indice_minimo: float | None
    indice_maximo: float | None
    url_imagem_colorida: str | None
    satelite: str = "Sentinel-2"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NDVIAlertaResumo(BaseModel):
    talhao_id: UUID
    talhao_nome: str
    tipo: Literal["QUEDA_VIGOR", "ESTRESSE_HIDRICO", "NUVEM_ALTA"]
    severidade: Literal["CRITICO", "ATENCAO"]
    titulo: str
    detalhe: str
    indice_atual: float | None = None
    variacao_pct: float | None = None
    cobertura_nuvens_pct: float | None = None


class NDVITalhaoResumo(BaseModel):
    talhao_id: UUID
    talhao_nome: str
    tipo_area: str
    area_hectares: float | None
    unidade_produtiva_id: UUID
    total_imagens: int
    indice_atual: float | None
    indice_anterior: float | None
    variacao_pct: float | None
    cobertura_nuvens_pct: float | None
    ultima_captura: date | None
    tendencia: Literal["SUBINDO", "CAINDO", "ESTAVEL"] | None
    classificacao: str
    satelite: str | None


class NDVIResumoPropriedadeResponse(BaseModel):
    unidade_produtiva_id: UUID | None
    periodo_dias: int | None
    total_areas_produtivas: int
    areas_monitoradas: int
    total_registros: int
    media_ndvi_propriedade: float | None
    variacao_media_pct: float | None
    classificacao_geral: str
    sincronizacao_automatica_disponivel: bool = False
    talhoes: list[NDVITalhaoResumo]
    alertas: list[NDVIAlertaResumo]
