from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PecuariaDashboardResumoExecutivoResponse(BaseModel):
    animais_ativos: int = Field(ge=0)
    lotes_ativos: int = Field(ge=0)
    piquetes_ativos: int = Field(ge=0)
    peso_total_kg: float = Field(ge=0)
    peso_medio_kg: float = Field(ge=0)
    manejos_pendentes: int = Field(ge=0)
    vacinacoes_pendentes: int = Field(ge=0)
    custo_sanitario_acumulado: float = Field(ge=0)
    area_pastagem_ha: float = Field(0.0, ge=0)
    lotacao_ua_ha: float = Field(0.0, ge=0)
    arrobas_totais: float = Field(0.0, ge=0)
    arrobas_por_hectare: float = Field(0.0, ge=0)
    custo_total_por_arroba: float = Field(0.0, ge=0)

    model_config = ConfigDict(from_attributes=True)

