from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.dre.schemas import DREWarning


class RecomendacaoAgricolaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    id: str
    label: str
    tipo: Literal[
        "REVISAO_OPERACAO",
        "INSPECAO_EQUIPAMENTO",
        "REVISAO_JORNADA",
        "ANALISE_PRODUCTION_UNIT",
        "INVESTIGACAO_MARGEM_NEGATIVA",
        "REVISAO_CUSTO_HECTARE",
        "REVISAO_RECONCILIACAO_ECONOMICA",
        "AUDITORIA_INCONSISTENCIA_OPERACIONAL",
        "ANALISE_SAFRA_BENCHMARK",
    ]
    severidade: Literal["INFO", "ATENCAO", "RISCO_OPERACIONAL", "RISCO_ECONOMICO"]
    origem_diagnostica_codigo: str
    origem_diagnostica_titulo: str
    contexto_operacional: str
    contexto_economico: str
    explicacao_objetiva: str
    acao_sugerida: str
    entidade_tipo: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    entidade_id: str
    entidade_label: str
    status: Literal["NOVA", "VISUALIZADA", "ACEITA", "IGNORADA"] = "NOVA"
    warnings_relevantes: list[str] = Field(default_factory=list)
    posicao: int | None = None


class RecomendacaoAgricolaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int = 0
    nova: int = 0
    visualizada: int = 0
    aceita: int = 0
    ignorada: int = 0
    info: int = 0
    atencao: int = 0
    risco_operacional: int = 0
    risco_economico: int = 0
    por_tipo: dict[str, int] = Field(default_factory=dict)


class RecomendacaoAgricolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    gerado_em: datetime
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    recomendacoes: list[RecomendacaoAgricolaItem] = Field(default_factory=list)
    resumo: RecomendacaoAgricolaResumo = Field(default_factory=RecomendacaoAgricolaResumo)
    warnings: list[DREWarning] = Field(default_factory=list)
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None

