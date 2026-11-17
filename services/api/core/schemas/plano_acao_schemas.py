from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

StatusPlanoAcao = Literal["ABERTO", "EM_ANDAMENTO", "CONCLUIDO", "ATRASADO"]


class PlanoAcaoCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    descricao: Optional[str] = None
    origem_indicador: Optional[str] = Field(None, max_length=100)
    unidade_produtiva_id: Optional[UUID] = None
    safra_id: Optional[UUID] = None
    tarefa_id: Optional[UUID] = None
    responsavel_id: Optional[UUID] = None
    responsavel_nome: Optional[str] = Field(None, max_length=150)
    meta: Optional[str] = Field(None, max_length=255)
    prazo: Optional[date] = None


class PlanoAcaoUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3, max_length=200)
    descricao: Optional[str] = None
    responsavel_id: Optional[UUID] = None
    responsavel_nome: Optional[str] = Field(None, max_length=150)
    meta: Optional[str] = Field(None, max_length=255)
    prazo: Optional[date] = None
    status: Optional[StatusPlanoAcao] = None
    resultado_obtido: Optional[str] = None


class PlanoAcaoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    unidade_produtiva_id: Optional[UUID] = None
    safra_id: Optional[UUID] = None
    tarefa_id: Optional[UUID] = None
    responsavel_id: Optional[UUID] = None
    titulo: str
    descricao: Optional[str] = None
    origem_indicador: Optional[str] = None
    responsavel_nome: Optional[str] = None
    meta: Optional[str] = None
    prazo: Optional[date] = None
    status: str
    resultado_obtido: Optional[str] = None
    concluido_em: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
