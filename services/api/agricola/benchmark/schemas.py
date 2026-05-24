from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.dre.schemas import DREWarning


class BenchmarkAgricolaItem(BaseModel):
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
    custo_operacional_total: float = 0.0
    custo_operacional_por_hectare: float | None = None
    custo_operacional_por_operacao: float | None = None
    horas_por_hectare: float | None = None
    hectares_por_jornada: float | None = None
    quantidade_operacoes: int = 0
    quantidade_jornadas: int = 0
    quantidade_apontamentos: int = 0
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None
    warnings_relevantes: list[str] = Field(default_factory=list)
    posicao: int | None = None
    destaque: Literal["MELHOR", "REFERENCIA", "PONTO_ATENCAO"] | None = None


class BenchmarkAgricolaDestaques(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    melhor: BenchmarkAgricolaItem | None = None
    referencia: BenchmarkAgricolaItem | None = None
    ponto_atencao: BenchmarkAgricolaItem | None = None


class BenchmarkAgricolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    gerado_em: datetime
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    data_inicio: date | None = None
    data_fim: date | None = None

    safra: BenchmarkAgricolaItem
    production_units: list[BenchmarkAgricolaItem] = Field(default_factory=list)
    ranking: list[BenchmarkAgricolaItem] = Field(default_factory=list)
    destaques: BenchmarkAgricolaDestaques = Field(default_factory=BenchmarkAgricolaDestaques)
    warnings: list[DREWarning] = Field(default_factory=list)
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None
