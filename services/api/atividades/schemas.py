from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class AtividadeItem(BaseModel):
    id: str
    tipo: str
    descricao: str
    data: datetime
    origem: str
    origem_id: Optional[str] = None
    meta: dict = {}
