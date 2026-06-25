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

    model_config = ConfigDict(from_attributes=True)

