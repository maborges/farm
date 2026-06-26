from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoteIndicadoresResponse(BaseModel):
    lote_id: UUID
    nome_lote: str
    quantidade_animais: int = Field(ge=0)
    peso_total_kg: float = Field(ge=0)
    peso_medio_kg: float = Field(ge=0)
    gmd_medio_kg_dia: float | None = None
    ultima_pesagem: date | None = None
    custo_sanitario_total: float = Field(ge=0)
    custo_sanitario_por_cabeca: float = Field(ge=0)
    custo_sanitario_por_kg: float = Field(ge=0)
    custo_sanitario_por_arroba: float = Field(ge=0)
    custo_aquisicao_total: float = Field(0, ge=0)

    model_config = ConfigDict(from_attributes=True)
