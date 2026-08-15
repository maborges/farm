from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agricola.receituario_agronomico.models import StatusReceituario


class ReceituarioItemCreate(BaseModel):
    produto_id: UUID
    dose: float = Field(gt=0)
    unidade_dose: str
    cultura: str | None = None
    praga_alvo: str | None = None


class ReceituarioItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    produto_id: UUID
    dose: float
    unidade_dose: str
    cultura: str | None
    praga_alvo: str | None
    carencia_dias: int | None


class ReceituarioAgronomicoCreate(BaseModel):
    numero: str | None = None
    agronomo_pessoa_id: UUID
    unidade_produtiva_id: UUID
    safra_id: UUID | None = None
    talhao_id: UUID | None = None
    operacao_agricola_id: UUID | None = None
    cultura: str | None = None
    praga_alvo: str | None = None
    data_emissao: date
    validade_dias: int = Field(default=90, gt=0)
    observacoes: str | None = None
    itens: list[ReceituarioItemCreate] = Field(min_length=1)


class ReceituarioAgronomicoUpdate(BaseModel):
    cultura: str | None = None
    praga_alvo: str | None = None
    observacoes: str | None = None
    itens: list[ReceituarioItemCreate] | None = None


class ReceituarioAgronomicoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    numero: str | None
    agronomo_pessoa_id: UUID
    crea_numero: str
    crea_uf: str
    unidade_produtiva_id: UUID
    safra_id: UUID | None
    talhao_id: UUID | None
    operacao_agricola_id: UUID | None
    cultura: str | None
    praga_alvo: str | None
    data_emissao: date
    data_validade: date
    status: StatusReceituario
    arquivo_pdf_url: str | None
    observacoes: str | None
    motivo_cancelamento: str | None
    itens: list[ReceituarioItemRead] = []
    created_at: datetime
    updated_at: datetime


class ReceituarioCancelarRequest(BaseModel):
    motivo: str = Field(min_length=3)


class ReceituarioUploadPdfResponse(BaseModel):
    arquivo_pdf_url: str
    status: StatusReceituario
