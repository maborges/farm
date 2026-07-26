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


class PlanoOperacionalTarefaInsumoCreate(BaseModel):
    safra_tarefa_necessidade_id: Optional[UUID] = None
    produto_id: UUID
    deposito_id: Optional[UUID] = None
    dose_planejada: Optional[float] = None
    unidade_dose: str = Field(..., min_length=1, max_length=20)
    quantidade_planejada: float = Field(..., gt=0)


class PlanoOperacionalTarefaInsumoUpdate(BaseModel):
    produto_id: Optional[UUID] = None
    deposito_id: Optional[UUID] = None
    dose_planejada: Optional[float] = None
    unidade_dose: Optional[str] = None
    quantidade_planejada: Optional[float] = Field(None, gt=0)


class PlanoOperacionalTarefaInsumoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plano_operacional_tarefa_id: UUID
    safra_tarefa_necessidade_id: Optional[UUID]
    produto_id: UUID
    deposito_id: Optional[UUID]
    dose_planejada: Optional[float]
    unidade_dose: str
    quantidade_planejada: float
    quantidade_disponivel_snapshot: Optional[float]
    quantidade_reservada: Optional[float]
    quantidade_faltante: Optional[float]
    custo_unitario_snapshot: Optional[float]
    custo_total_estimado: Optional[float]
    fonte_custo: Optional[str]
    substitui_item_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
