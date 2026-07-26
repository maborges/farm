from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime, date
from typing import Optional


class PlanoOperacionalCreate(BaseModel):
    safra_id: UUID
    production_unit_id: Optional[UUID] = None
    nome: str = Field(..., min_length=3, max_length=150)
    descricao: Optional[str] = None
    data_inicio_prevista: date
    data_fim_prevista: Optional[date] = None


class PlanoOperacionalUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    descricao: Optional[str] = None
    data_inicio_prevista: Optional[date] = None
    data_fim_prevista: Optional[date] = None


class PlanoOperacionalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    safra_id: UUID
    production_unit_id: Optional[UUID]
    nome: str
    descricao: Optional[str]
    data_inicio_prevista: date
    data_fim_prevista: Optional[date]
    status: str
    versao: int
    criado_por: Optional[UUID]
    aprovado_por: Optional[UUID]
    aprovado_em: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class PlanoOperacionalTarefaCreate(BaseModel):
    safra_tarefa_id: UUID


class PlanoOperacionalTarefaUpdate(BaseModel):
    status_planejamento: Optional[str] = None
    data_programada: Optional[date] = None
    observacao: Optional[str] = None
    ordem_execucao: Optional[int] = None


class PlanoOperacionalTarefaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plano_operacional_id: UUID
    safra_tarefa_id: UUID
    status_planejamento: str
    data_programada: Optional[date]
    observacao: Optional[str]
    ordem_execucao: Optional[int]
    created_at: datetime
    updated_at: datetime
