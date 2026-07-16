from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
import uuid

from .unidade_produtiva_input import UnidadeProdutivaCreate, UnidadeProdutivaUpdate

class CadastroCompletoCreate(UnidadeProdutivaCreate):
    propriedade_id: Optional[uuid.UUID] = Field(None, description="ID da Propriedade se já conhecida")
    imovel_rural_id: Optional[uuid.UUID] = Field(None, description="ID do Imóvel Rural se já conhecido")
    propriedade_imovel_id: Optional[uuid.UUID] = Field(None, description="ID do vínculo se já conhecido")

class CadastroCompletoUpdate(UnidadeProdutivaUpdate):
    propriedade_id: Optional[uuid.UUID] = Field(None, description="ID da Propriedade se já conhecida")
    imovel_rural_id: Optional[uuid.UUID] = Field(None, description="ID do Imóvel Rural se já conhecido")
    propriedade_imovel_id: Optional[uuid.UUID] = Field(None, description="ID do vínculo se já conhecido")
