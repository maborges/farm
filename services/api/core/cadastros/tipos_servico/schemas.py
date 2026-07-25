from pydantic import BaseModel, computed_field
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
    tenant_id: Optional[uuid.UUID]
    nome: str
    unidade_medida: str
    custo_referencia: Optional[Decimal]
    observacoes: Optional[str]
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[misc]
    @property
    def is_global(self) -> bool:
        """Catálogo padrão do sistema (tenant_id NULL) — somente leitura para o tenant."""
        return self.tenant_id is None
