from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pecuaria.animal.models import CategoriaAnimal, EspecieAnimal, SexoAnimal, StatusAnimal


class AnimalBase(BaseModel):
    lote_id: UUID | None = None
    pai_id: UUID | None = None
    mae_id: UUID | None = None
    numero_brinco: str | None = Field(None, max_length=50)
    numero_sisbov: str | None = Field(None, max_length=50)
    microchip: str | None = Field(None, max_length=100)
    nome: str | None = Field(None, max_length=100)

    especie: EspecieAnimal = EspecieAnimal.BOVINO
    categoria: CategoriaAnimal = CategoriaAnimal.BEZERRO
    raca: str | None = Field(None, max_length=100)
    sexo: SexoAnimal = SexoAnimal.MACHO
    pelagem: str | None = Field(None, max_length=100)

    data_nascimento: date | None = None
    data_entrada: date | None = None

    status: StatusAnimal = StatusAnimal.ATIVO
    peso_atual_kg: float | None = Field(None, ge=0)
    data_ultima_pesagem: date | None = None

    valor_aquisicao: float | None = Field(None, ge=0)
    valor_atual: float | None = Field(None, ge=0)
    dados_extras: dict | None = None
    observacoes: str | None = None


class AnimalCreate(AnimalBase):
    unidade_produtiva_id: UUID
    fornecedor: str | None = Field(None, max_length=150)
    numero_nf: str | None = Field(None, max_length=20)
    serie_nf: str | None = Field(None, max_length=5)
    chave_nfe: str | None = Field(None, max_length=44)

    @model_validator(mode="after")
    def validate_identifiers(self) -> "AnimalCreate":
        if not self.numero_brinco and not self.numero_sisbov and not self.microchip:
            raise ValueError(
                "Ao menos um identificador "
                "(numero_brinco, numero_sisbov ou microchip) deve ser fornecido."
            )
        return self


class AnimalUpdate(BaseModel):
    lote_id: UUID | None = None
    pai_id: UUID | None = None
    mae_id: UUID | None = None
    numero_brinco: str | None = Field(None, max_length=50)
    numero_sisbov: str | None = Field(None, max_length=50)
    microchip: str | None = Field(None, max_length=100)
    nome: str | None = Field(None, max_length=100)
    especie: EspecieAnimal | None = None
    categoria: CategoriaAnimal | None = None
    raca: str | None = Field(None, max_length=100)
    sexo: SexoAnimal | None = None
    pelagem: str | None = Field(None, max_length=100)
    data_nascimento: date | None = None
    data_entrada: date | None = None
    status: StatusAnimal | None = None
    peso_atual_kg: float | None = Field(None, ge=0)
    data_ultima_pesagem: date | None = None
    valor_aquisicao: float | None = Field(None, ge=0)
    valor_atual: float | None = Field(None, ge=0)
    dados_extras: dict | None = None
    fornecedor: str | None = Field(None, max_length=150)
    numero_nf: str | None = Field(None, max_length=20)
    serie_nf: str | None = Field(None, max_length=5)
    chave_nfe: str | None = Field(None, max_length=44)
    observacoes: str | None = None


class AnimalResponse(AnimalBase):
    id: UUID
    tenant_id: UUID
    unidade_produtiva_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnimalListResponse(BaseModel):
    items: list[AnimalResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AnimalFilter(BaseModel):
    q: str | None = None
    lote_id: UUID | None = None
    categoria: CategoriaAnimal | None = None
    status: StatusAnimal | None = None
    sexo: SexoAnimal | None = None
    especie: EspecieAnimal | None = None
