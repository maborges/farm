from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ContagemAbrirRequest(BaseModel):
    deposito_id: uuid.UUID
    observacoes: str | None = None


class ContagemItemRegistrarRequest(BaseModel):
    quantidade_contada: float = Field(..., ge=0)


class ContagemEstoqueItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contagem_id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: str | None = None
    quantidade_sistema: float
    quantidade_contada: float | None
    divergencia: float | None = None
    contado_em: datetime | None
    movimento_ajuste_id: uuid.UUID | None


class ContagemEstoqueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deposito_id: uuid.UUID
    status: str
    aberta_por: uuid.UUID | None
    aberta_em: datetime
    concluida_por: uuid.UUID | None
    concluida_em: datetime | None
    observacoes: str | None
    itens: list[ContagemEstoqueItemResponse] = []
