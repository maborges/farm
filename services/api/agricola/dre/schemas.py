from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DREWarning(BaseModel):
    codigo: str
    titulo: str
    severidade: str
    mensagem: str
    origem: str
    amostras: list[str] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


class DRESourceItem(BaseModel):
    natureza: str
    fonte_oficial: str
    origem_tipo: str | None = None
    origem_id: UUID | None = None
    production_unit_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    safra_id: UUID | None = None
    valor: float = 0.0
    deduplicado: bool = False
    motivo: str | None = None
    meta: dict = Field(default_factory=dict)


class DREAgricolaSection(BaseModel):
    valor: float = 0.0
    itens: list[DRESourceItem] = Field(default_factory=list)
    total_registros: int = 0
    fontes: dict[str, float] = Field(default_factory=dict)


class DREReconcilacaoMeta(BaseModel):
    lancamentos_financeiros_receita: float = 0.0
    lancamentos_financeiros_custo: float = 0.0
    lancamentos_financeiros_total: float = 0.0
    estoque_movimentos_com_custo: int = 0
    cost_allocations_total: int = 0
    despesas_excluidas_por_precedencia: int = 0
    receitas_excluidas_por_precedencia: int = 0
    observacao: str | None = None
    detalhes: dict = Field(default_factory=dict)


class DRELoteMargem(BaseModel):
    produto_colhido_id: UUID
    production_unit_id: UUID | None = None
    quantidade: float = 0.0
    unidade: str | None = None
    receita_total: float = 0.0
    custo_rateado: float = 0.0
    margem: float = 0.0
    margem_percentual: float | None = None


class DREAgricolaKpis(BaseModel):
    area_total_ha: float = 0.0
    receita_liquida: float = 0.0
    custo_operacional_total: float = 0.0
    margem_bruta: float = 0.0
    resultado_operacional: float = 0.0
    margem_pct: float | None = None
    custo_por_hectare: float | None = None
    receita_por_hectare: float | None = None
    resultado_por_hectare: float | None = None
    sujeito_reconciliacao: bool = False
    observacao_reconciliacao: str | None = None
    warnings_relevantes: list[str] = Field(default_factory=list)


class DREAgricolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    gerado_em: datetime

    safra_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    production_unit_id: UUID | None = None
    unidade_operacional_id: UUID | None = None
    cultura: str | None = None

    production_unit_ids: list[UUID] = Field(default_factory=list)

    receita_bruta: float = 0.0
    deducoes: float = 0.0
    receita_liquida: float = 0.0
    custos_diretos: float = 0.0
    custos_operacionais: float = 0.0
    margem_bruta: float = 0.0
    despesas_operacionais: float = 0.0
    resultado_operacional: float = 0.0

    receita: DREAgricolaSection = Field(default_factory=DREAgricolaSection)
    custos_diretos_detalhe: DREAgricolaSection = Field(default_factory=DREAgricolaSection)
    custos_operacionais_detalhe: DREAgricolaSection = Field(default_factory=DREAgricolaSection)
    despesas_operacionais_detalhe: DREAgricolaSection = Field(default_factory=DREAgricolaSection)
    kpis: DREAgricolaKpis = Field(default_factory=DREAgricolaKpis)

    margem_por_lote: list[DRELoteMargem] = Field(default_factory=list)
    lotes_sem_vinculo: int = 0

    warnings: list[DREWarning] = Field(default_factory=list)
    reconciliacao: DREReconcilacaoMeta = Field(default_factory=DREReconcilacaoMeta)
