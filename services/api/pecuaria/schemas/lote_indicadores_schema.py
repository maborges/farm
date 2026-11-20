from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoteIndicadoresResponse(BaseModel):
    lote_id: UUID
    nome_lote: str
    modo_gestao: str = "POR_LOTE"
    rendimento_carcaca_pct: float = Field(50.0, gt=0, le=100)
    quantidade_animais: int = Field(ge=0)
    peso_total_kg: float = Field(ge=0)
    peso_medio_kg: float = Field(ge=0)
    arrobas_totais: float = Field(0.0, ge=0)
    arrobas_produzidas: float = Field(0.0, ge=0)
    gmd_medio_kg_dia: float | None = None
    ultima_pesagem: date | None = None
    custo_sanitario_total: float = Field(ge=0)
    custo_sanitario_por_cabeca: float = Field(ge=0)
    custo_sanitario_por_kg: float = Field(ge=0)
    custo_sanitario_por_arroba: float = Field(ge=0)
    custo_aquisicao_total: float = Field(0, ge=0)
    area_piquete_ha: float = Field(0.0, ge=0)
    lotacao_ua_ha: float = Field(0.0, ge=0)
    arrobas_por_hectare: float = Field(0.0, ge=0)
    custo_nutricao_total: float = Field(0.0, ge=0)
    custo_outros_total: float = Field(0.0, ge=0)
    custo_total_operacional: float = Field(0.0, ge=0)
    custo_total_por_arroba: float = Field(0.0, ge=0)
    custo_por_arroba_produzida: float = Field(0.0, ge=0)
    custo_break_even_por_arroba: float = Field(0.0, ge=0)
    cotacao_arroba_referencia: float | None = Field(None, ge=0)
    fonte_cotacao: str | None = None
    valor_mercado_estimado: float | None = Field(None, ge=0)
    margem_bruta_estimada: float | None = None
    margem_estimada_por_cabeca: float | None = None

    model_config = ConfigDict(from_attributes=True)
