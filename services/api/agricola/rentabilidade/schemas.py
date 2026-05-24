from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.dre.schemas import DREWarning


class RentabilidadeAgricolaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope: Literal["SAFRA", "PRODUCTION_UNIT"]
    id: UUID
    label: str
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    area_total_ha: float = 0.0
    resultado_operacional: float = 0.0
    margem_pct: float | None = None
    receita_liquida_por_hectare: float | None = None
    resultado_por_hectare: float | None = None
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None
    warnings_relevantes: list[str] = Field(default_factory=list)
    posicao: int | None = None


class RentabilidadeAgricolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    gerado_em: datetime
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    data_inicio: date | None = None
    data_fim: date | None = None

    safra: RentabilidadeAgricolaItem
    production_units: list[RentabilidadeAgricolaItem] = Field(default_factory=list)
    ranking: list[RentabilidadeAgricolaItem] = Field(default_factory=list)
    warnings: list[DREWarning] = Field(default_factory=list)
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None
