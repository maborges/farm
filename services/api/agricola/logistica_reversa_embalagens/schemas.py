from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.logistica_reversa_embalagens.models import StatusDevolucaoEmbalagem


class DevolucaoEmbalagemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_recebimento_id: UUID
    produto_id: UUID
    quantidade_embalagens_compradas: int
    quantidade_embalagens_devolvidas: int
    data_compra: date
    prazo_limite: date
    destino_pessoa_id: UUID | None
    status: StatusDevolucaoEmbalagem
    comprovante_pdf_url: str | None
    observacoes: str | None
    created_at: datetime
    updated_at: datetime


class RegistrarDevolucaoRequest(BaseModel):
    quantidade_embalagens: int = Field(gt=0)
    destino_pessoa_id: UUID | None = None
    observacoes: str | None = None
