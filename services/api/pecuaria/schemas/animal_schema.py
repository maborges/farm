from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from datetime import date, datetime
from uuid import UUID

from pecuaria.animal.models import EspecieAnimal, SexoAnimal, CategoriaAnimal, StatusAnimal

class AnimalBase(BaseModel):
    lote_id: Optional[UUID] = None
    pai_id: Optional[UUID] = None
    mae_id: Optional[UUID] = None
    numero_brinco: Optional[str] = Field(None, max_length=50)
    numero_sisbov: Optional[str] = Field(None, max_length=50)
    microchip: Optional[str] = Field(None, max_length=100)
    nome: Optional[str] = Field(None, max_length=100)
    
    especie: EspecieAnimal = EspecieAnimal.BOVINO
    categoria: CategoriaAnimal = CategoriaAnimal.BEZERRO
    raca: Optional[str] = Field(None, max_length=100)
    sexo: SexoAnimal = SexoAnimal.MACHO
    pelagem: Optional[str] = Field(None, max_length=100)
    
    data_nascimento: Optional[date] = None
    data_entrada: Optional[date] = None
    
    status: StatusAnimal = StatusAnimal.ATIVO
    peso_atual_kg: Optional[float] = Field(None, ge=0)
    data_ultima_pesagem: Optional[date] = None
    
    valor_aquisicao: Optional[float] = Field(None, ge=0)
    valor_atual: Optional[float] = Field(None, ge=0)
    observacoes: Optional[str] = None


class AnimalCreate(AnimalBase):
    unidade_produtiva_id: UUID

    @model_validator(mode="after")
    def validate_identifiers(self) -> "AnimalCreate":
        if not self.numero_brinco and not self.numero_sisbov and not self.microchip:
            raise ValueError("Ao menos um identificador (numero_brinco, numero_sisbov ou microchip) deve ser fornecido.")
        return self


class AnimalUpdate(BaseModel):
    lote_id: Optional[UUID] = None
    pai_id: Optional[UUID] = None
    mae_id: Optional[UUID] = None
    numero_brinco: Optional[str] = Field(None, max_length=50)
    numero_sisbov: Optional[str] = Field(None, max_length=50)
    microchip: Optional[str] = Field(None, max_length=100)
    nome: Optional[str] = Field(None, max_length=100)
    especie: Optional[EspecieAnimal] = None
    categoria: Optional[CategoriaAnimal] = None
    raca: Optional[str] = Field(None, max_length=100)
    sexo: Optional[SexoAnimal] = None
    pelagem: Optional[str] = Field(None, max_length=100)
    data_nascimento: Optional[date] = None
    data_entrada: Optional[date] = None
    status: Optional[StatusAnimal] = None
    peso_atual_kg: Optional[float] = Field(None, ge=0)
    data_ultima_pesagem: Optional[date] = None
    valor_aquisicao: Optional[float] = Field(None, ge=0)
    valor_atual: Optional[float] = Field(None, ge=0)
    observacoes: Optional[str] = None


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
    q: Optional[str] = None
    lote_id: Optional[UUID] = None
    categoria: Optional[CategoriaAnimal] = None
    status: Optional[StatusAnimal] = None
    sexo: Optional[SexoAnimal] = None
    especie: Optional[EspecieAnimal] = None
