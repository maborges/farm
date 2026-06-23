import asyncio
from pydantic import BaseModel, Field, ValidationError
from decimal import Decimal
from typing import Optional

class UnidadeProdutivaCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    tipo_propriedade: Optional[str] = Field("fazenda", max_length=30)
    cpf_cnpj: Optional[str] = Field(None, max_length=18)
    inscricao_estadual: Optional[str] = Field(None, max_length=50)
    uf: Optional[str] = Field(None, min_length=2, max_length=2)
    area_total_ha: Optional[Decimal] = Field(None, gt=0)
    area_app_ha: Optional[Decimal] = Field(None, ge=0)

data = {
    "nome": "Fazenda Teste",
    "tipo_propriedade": "fazenda",
    "cpf_cnpj": "",
    "inscricao_estadual": "",
    "uf": "",
    "area_total_ha": 0,
    "area_app_ha": 0
}

try:
    obj = UnidadeProdutivaCreate(**data)
    print("Success")
except ValidationError as e:
    print(e.json())

