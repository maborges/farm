from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class NotificacaoCreate(BaseModel):
    tipo: str
    titulo: str
    mensagem: str
    nivel: str = "INFO"
    origem: Optional[str] = None
    origem_id: Optional[str] = None
    meta: dict = {}


class NotificacaoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tipo: str
    titulo: str
    mensagem: str
    nivel: str
    lida: bool
    origem: Optional[str] = None
    origem_id: Optional[str] = None
    meta: dict
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MarcarLidasRequest(BaseModel):
    ids: Optional[list[UUID]] = None  # None = mark all

class NotificacaoPreferenciaUpdate(BaseModel):
    email_ativo: bool
    sistema_ativo: bool

class NotificacaoPreferenciaResponse(BaseModel):
    tipo: str
    email_ativo: bool
    sistema_ativo: bool
    
    model_config = ConfigDict(from_attributes=True)
