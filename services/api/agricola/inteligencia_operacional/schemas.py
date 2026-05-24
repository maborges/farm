from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.dre.schemas import DREWarning

SeveridadeCanonica = Literal["INFO", "ATENCAO", "RISCO_OPERACIONAL", "RISCO_ECONOMICO", "PRIORIDADE_CRITICA"]
OrigemAnalitica = Literal["PRIORIDADE", "DIAGNOSTICO", "RECOMENDACAO"]


class PlanoAcaoOperacionalAgricolaFonte(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    origem_analitica: OrigemAnalitica
    codigo: str
    titulo: str
    severidade: SeveridadeCanonica
    scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY", "TENANT"]
    entidade_tipo: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    entidade_id: str
    entidade_label: str


class PlanoAcaoOperacionalAgricolaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chave: str
    scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    titulo: str
    resumo: str
    motivo: str
    severidade: SeveridadeCanonica
    impacto_estimado: float | None = None
    acoes_sugeridas: list[str] = Field(default_factory=list)
    prazo_sugerido: str
    contexto_operacional: str
    origem_primaria: PlanoAcaoOperacionalAgricolaFonte
    fontes_analiticas: list[PlanoAcaoOperacionalAgricolaFonte] = Field(default_factory=list)
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    entidade_tipo: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    entidade_id: str
    entidade_label: str
    posicao: int | None = None


class PlanoAcaoOperacionalAgricolaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int = 0
    info: int = 0
    atencao: int = 0
    risco_operacional: int = 0
    risco_economico: int = 0
    prioridade_critica: int = 0
    por_origem: dict[str, int] = Field(default_factory=dict)
    por_entidade_tipo: dict[str, int] = Field(default_factory=dict)
    por_prazo: dict[str, int] = Field(default_factory=dict)


class PlanoAcaoOperacionalAgricolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    gerado_em: datetime
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    planos: list[PlanoAcaoOperacionalAgricolaItem] = Field(default_factory=list)
    resumo: PlanoAcaoOperacionalAgricolaResumo = Field(default_factory=PlanoAcaoOperacionalAgricolaResumo)
    warnings: list[DREWarning] = Field(default_factory=list)
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None

