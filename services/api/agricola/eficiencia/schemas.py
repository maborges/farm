from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.dre.schemas import DREWarning


class EficienciaOperacionalItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION"]
    id: str
    label: str
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    equipamento_id: UUID | None = None
    operacao_id: UUID | None = None
    area_total_ha: float = 0.0
    hectares_totais: float = 0.0
    horas_totais: float = 0.0
    quantidade_operacoes: int = 0
    quantidade_jornadas: int = 0
    quantidade_apontamentos: int = 0
    custo_operacional_total: float = 0.0
    custo_operacional_por_hectare: float | None = None
    custo_operacional_por_operacao: float | None = None
    horas_por_hectare: float | None = None
    hectares_por_jornada: float | None = None
    resultado_operacional: float | None = None
    resultado_por_hectare: float | None = None
    margem_pct: float | None = None
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None
    warnings_relevantes: list[str] = Field(default_factory=list)
    posicao: int | None = None


class EficienciaOperacionalAgricolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    gerado_em: datetime
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    data_inicio: date | None = None
    data_fim: date | None = None

    safra: EficienciaOperacionalItem
    production_units: list[EficienciaOperacionalItem] = Field(default_factory=list)
    equipamentos: list[EficienciaOperacionalItem] = Field(default_factory=list)
    operacoes: list[EficienciaOperacionalItem] = Field(default_factory=list)
    ranking: list[EficienciaOperacionalItem] = Field(default_factory=list)
    warnings: list[DREWarning] = Field(default_factory=list)
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None

