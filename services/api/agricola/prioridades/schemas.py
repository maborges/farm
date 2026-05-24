from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.dre.schemas import DREWarning


class PrioridadeAgricolaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    id: str
    label: str
    tipo: Literal[
        "MARGEM_ABAIXO_MEDIA_TENANT",
        "CUSTO_HECTARE_ACIMA_MEDIA",
        "PRODUCTION_UNIT_BAIXA_EFICIENCIA",
        "EQUIPAMENTO_CUSTO_ELEVADO",
        "JORNADA_BAIXA_PRODUTIVIDADE",
        "RESULTADO_OPERACIONAL_NEGATIVO",
        "RESULTADO_SAFRA_ABAIXO_BENCHMARK",
        "RECORRENCIA_WARNING_ECONOMICO",
        "RECORRENCIA_INCONSISTENCIA_OPERACIONAL",
    ]
    severidade: Literal["INFO", "ATENCAO", "RISCO_OPERACIONAL", "RISCO_ECONOMICO", "PRIORIDADE_CRITICA"]
    score_prioridade: int
    origem: Literal["DIAGNOSTICO", "RECOMENDACAO", "BENCHMARK", "WARNING"]
    origem_codigo: str
    origem_titulo: str
    impacto_estimado: float | None = None
    contexto_operacional: str
    contexto_economico: str
    acao_sugerida: str
    entidade_tipo: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    entidade_id: str
    entidade_label: str
    status: Literal["NOVA", "VISUALIZADA", "EM_ANALISE", "RESOLVIDA", "IGNORADA"] = "NOVA"
    warnings_relevantes: list[str] = Field(default_factory=list)
    recorrencia: int = 1
    fontes_relacionadas: list[str] = Field(default_factory=list)
    posicao: int | None = None


class PrioridadeAgricolaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int = 0
    nova: int = 0
    visualizada: int = 0
    em_analise: int = 0
    resolvida: int = 0
    ignorada: int = 0
    info: int = 0
    atencao: int = 0
    risco_operacional: int = 0
    risco_economico: int = 0
    prioridade_critica: int = 0
    por_origem: dict[str, int] = Field(default_factory=dict)
    por_tipo: dict[str, int] = Field(default_factory=dict)


class PrioridadeAgricolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    gerado_em: datetime
    safra_id: UUID
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    prioridades: list[PrioridadeAgricolaItem] = Field(default_factory=list)
    resumo: PrioridadeAgricolaResumo = Field(default_factory=PrioridadeAgricolaResumo)
    warnings: list[DREWarning] = Field(default_factory=list)
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None


class PrioridadeAgricolaStatusUpdate(BaseModel):
    status: Literal["NOVA", "VISUALIZADA", "EM_ANALISE", "RESOLVIDA", "IGNORADA"]
    observacao: str | None = Field(default=None, max_length=240)


class PrioridadeAgricolaComentarioCreate(BaseModel):
    comentario: str = Field(..., min_length=1, max_length=240)


class PrioridadeAgricolaHistoricoItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prioridade_id: str
    evento_tipo: Literal["STATUS", "COMENTARIO"]
    status_anterior: Literal["NOVA", "VISUALIZADA", "EM_ANALISE", "RESOLVIDA", "IGNORADA"] | None = None
    status_novo: Literal["NOVA", "VISUALIZADA", "EM_ANALISE", "RESOLVIDA", "IGNORADA"] | None = None
    observacao: str | None = None
    comentario: str | None = None
    responsavel_id: UUID | None = None
    responsavel_nome: str | None = None
    alterado_em: datetime


class PrioridadeAgricolaStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prioridade_id: str
    prioridade_status_id: UUID
    status_atual: Literal["NOVA", "VISUALIZADA", "EM_ANALISE", "RESOLVIDA", "IGNORADA"]
    historico: list[PrioridadeAgricolaHistoricoItem] = Field(default_factory=list)
    sujeito_reconciliacao: bool = False
