from pydantic import BaseModel, Field, ConfigDict
from datetime import date
from typing import Optional
from uuid import UUID

class PesagemCreate(BaseModel):
    data_evento: date = Field(..., description="Data em que o animal foi pesado")
    peso_kg: float = Field(..., gt=0, description="Peso em quilogramas (deve ser maior que zero)")
    observacoes: Optional[str] = Field(None, description="Observações adicionais (condição corporal, etc)")
    tarefa_campo_id: Optional[UUID] = Field(None, description="Opcional: Vínculo com a execução no módulo Campo")
    operador_id: Optional[UUID] = Field(None, description="Opcional: Operador que executou a tarefa")

class PesagemResponse(BaseModel):
    id: UUID
    animal_id: UUID
    data_evento: date
    peso_kg: float
    dias_desde_anterior: Optional[int] = Field(None, description="Quantidade de dias desde a última pesagem registrada")
    gmd_periodo: Optional[float] = Field(None, description="Ganho Médio Diário no período em kg/dia")
    observacoes: Optional[str] = None
    tarefa_campo_id: Optional[UUID] = None
    operador_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)
