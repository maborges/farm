from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class PlanoAcaoItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    safra_id: UUID
    tipo: str
    titulo: str
    descricao: str
    prioridade: str
    status: str
    rota: str
    origem: str
    created_at: datetime
    concluido_at: Optional[datetime] = None
    ignorado_at: Optional[datetime] = None


class PlanoAcaoStatusUpdate(BaseModel):
    status: str  # CONCLUIDA | IGNORADA
