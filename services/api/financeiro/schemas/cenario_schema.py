from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class CenarioSafraCreate(BaseModel):
    safra_id: UUID
    nome: str = Field(..., min_length=1, max_length=100)
    receita_percentual: float
    custos_percentual: float
    resultado_simulado: float
    margem_simulada: float


class CenarioSafraResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    safra_id: UUID
    nome: str
    receita_percentual: float
    custos_percentual: float
    resultado_simulado: float
    margem_simulada: float
    escolhido: bool
    escolhido_at: datetime | None = None
    recomendado_pela_ia: bool = False
    created_at: datetime


class AnaliseCenarioRealResponse(BaseModel):
    cenario_escolhido: str | None
    resultado_real: float
    resultado_planejado: float
    desvio: float
    desvio_percentual: float
