from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoteResumoSanitarioProdutoItem(BaseModel):
    produto_id: UUID
    nome: str
    quantidade_eventos: int = Field(ge=0)
    custo_total: float = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class LoteResumoSanitarioHistoricoItem(BaseModel):
    tarefa_campo_id: UUID
    produto_id: UUID
    produto_nome: str
    data_vacinacao: date | None = None
    quantidade_eventos: int = Field(ge=0)
    custo_total: float = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class LoteResumoSanitarioResponse(BaseModel):
    lote_id: UUID
    nome_lote: str
    quantidade_animais: int = Field(ge=0)
    eventos_sanitarios: int = Field(ge=0)
    vacinacoes: int = Field(ge=0)
    custo_sanitario_total: float = Field(ge=0)
    custo_sanitario_por_animal: float = Field(ge=0)
    ultima_vacinacao: date | None = None
    produto_mais_usado: LoteResumoSanitarioProdutoItem | None = None
    produtos_utilizados: list[LoteResumoSanitarioProdutoItem] = Field(default_factory=list)
    historico_sanitario_resumido: list[LoteResumoSanitarioHistoricoItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
