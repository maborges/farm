from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Literal


class FrotaRegraInteligenteBase(BaseModel):
    nome: str
    chave: str
    descricao: str | None = None
    ativa: bool = False
    threshold_valor: float | None = None
    acao_automatica: bool = False
    precisa_confirmacao: bool = True
    notificar_gestor: bool = True


class FrotaRegraInteligenteCreate(FrotaRegraInteligenteBase):
    pass


class FrotaRegraInteligenteUpdate(BaseModel):
    ativa: bool | None = None
    threshold_valor: float | None = None
    acao_automatica: bool | None = None
    precisa_confirmacao: bool | None = None
    notificar_gestor: bool | None = None


class FrotaRegraInteligenteSchema(FrotaRegraInteligenteBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


class FrotaLogAutomacaoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    regra_id: UUID
    equipamento_id: UUID | None = None
    acao_executada: str
    status: str
    justificativa: str | None = None
    threshold_atingido: float | None = None
    economia_estimada: float | None = None
    detalhe: str | None = None
    created_at: datetime
