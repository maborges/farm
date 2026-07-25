from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal
import uuid


class TipoServicoCreate(BaseModel):
    nome: str
    unidade_medida: str = "UN"
    custo_referencia: Optional[Decimal] = None
    observacoes: Optional[str] = None
    ativo: bool = True


class TipoServicoUpdate(BaseModel):
    nome: Optional[str] = None
    unidade_medida: Optional[str] = None
    custo_referencia: Optional[Decimal] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class TipoServicoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    unidade_medida: str
    custo_referencia: Optional[Decimal]
    observacoes: Optional[str]
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
