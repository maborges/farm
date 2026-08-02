from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class UnidadeMedidaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codigo: str
    nome: str
    dimensao: str


class ConversaoRequest(BaseModel):
    valor: Decimal
    unidade_origem_id: UUID
    unidade_destino_id: UUID
    cultura: str | None = None


class ConversaoResponse(BaseModel):
    valor_original: Decimal
    unidade_origem_id: UUID
    valor_convertido: Decimal
    unidade_destino_id: UUID
