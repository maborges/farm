from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.dre.schemas import DREWarning


class DiagnosticoAgricolaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY", "TENANT"]
    id: str
    label: str
    codigo: str
    titulo: str
    severidade: Literal["INFO", "ATENCAO", "RISCO_OPERACIONAL", "RISCO_ECONOMICO"]
    mensagem: str
    categoria: Literal["OPERACIONAL", "ECONOMICO", "RECORRENCIA"]
    valor_observado: float | None = None
    valor_referencia: float | None = None
    desvio_pct: float | None = None
    sugestao: str | None = None
    warnings_relevantes: list[str] = Field(default_factory=list)
    posicao: int | None = None


class DiagnosticoAgricolaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int = 0
    info: int = 0
    atencao: int = 0
    risco_operacional: int = 0
    risco_economico: int = 0


class DiagnosticoAgricolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    gerado_em: datetime
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    diagnosticos: list[DiagnosticoAgricolaItem] = Field(default_factory=list)
    ranking: list[DiagnosticoAgricolaItem] = Field(default_factory=list)
    resumo: DiagnosticoAgricolaResumo = Field(default_factory=DiagnosticoAgricolaResumo)
    warnings: list[DREWarning] = Field(default_factory=list)
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None

