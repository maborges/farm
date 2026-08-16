from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PlanoManutencaoBenfeitoriaCreate(BaseModel):
    benfeitoria_id: uuid.UUID
    descricao: str = Field(..., max_length=150)
    frequencia_dias: int | None = Field(None, gt=0)


class PlanoManutencaoBenfeitoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    benfeitoria_id: uuid.UUID
    descricao: str
    frequencia_dias: int | None
    ultimo_registro_data: datetime | None
    created_at: datetime


class OrdemServicoBenfeitoriaCreate(BaseModel):
    benfeitoria_id: uuid.UUID
    plano_manutencao_id: uuid.UUID | None = None
    safra_id: uuid.UUID | None = None
    talhao_id: uuid.UUID | None = None
    tipo: str = Field(..., description="PREVENTIVA | CORRETIVA")
    descricao_problema: str = Field(..., max_length=500)


class OrdemServicoBenfeitoriaConcluirRequest(BaseModel):
    custo_total: float = Field(0.0, ge=0)


class OrdemServicoBenfeitoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    benfeitoria_id: uuid.UUID
    plano_manutencao_id: uuid.UUID | None
    safra_id: uuid.UUID | None
    talhao_id: uuid.UUID | None
    numero_os: str
    tipo: str
    status: str
    descricao_problema: str
    data_abertura: datetime
    data_conclusao: datetime | None
    custo_total: float
