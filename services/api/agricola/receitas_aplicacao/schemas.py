from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class ReceitaAplicacaoInsumoCreate(BaseModel):
    produto_id: UUID
    deposito_id: Optional[UUID] = None
    dose_ha: float = Field(..., gt=0)
    unidade_dose: str = Field(..., min_length=1, max_length=20)


class ReceitaAplicacaoInsumoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    receita_id: UUID
    produto_id: UUID
    deposito_id: Optional[UUID]
    dose_ha: float
    unidade_dose: str


class ReceitaAplicacaoMaoObraCreate(BaseModel):
    tipo_servico_id: UUID
    funcao: Optional[str] = Field(None, max_length=100)
    quantidade_pessoas: int = Field(1, gt=0)
    horas_fixas: float = Field(0.0, ge=0)
    horas_por_hectare: float = Field(0.0, ge=0)


class ReceitaAplicacaoMaoObraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    receita_id: UUID
    tipo_servico_id: UUID
    funcao: Optional[str]
    quantidade_pessoas: int
    horas_fixas: float
    horas_por_hectare: float


class ReceitaAplicacaoCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150)
    tipo_operacao: Optional[str] = Field(None, max_length=50)
    insumos: List[ReceitaAplicacaoInsumoCreate] = Field(default_factory=list)
    mao_obra: List[ReceitaAplicacaoMaoObraCreate] = Field(default_factory=list)


class ReceitaAplicacaoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    tipo_operacao: Optional[str] = Field(None, max_length=50)
    ativo: Optional[bool] = None
    insumos: Optional[List[ReceitaAplicacaoInsumoCreate]] = None
    mao_obra: Optional[List[ReceitaAplicacaoMaoObraCreate]] = None


class ReceitaAplicacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    nome: str
    tipo_operacao: Optional[str]
    ativo: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    insumos: List[ReceitaAplicacaoInsumoResponse] = Field(default_factory=list)
    mao_obra: List[ReceitaAplicacaoMaoObraResponse] = Field(default_factory=list)


class AplicarReceitaRequest(BaseModel):
    receita_id: UUID
    plano_operacional_tarefa_ids: List[UUID] = Field(..., min_length=1)


class AplicarReceitaResultado(BaseModel):
    plano_operacional_tarefa_id: UUID
    insumos_criados: int
    mao_obra_criada: int


class AplicarReceitaResponse(BaseModel):
    resultados: List[AplicarReceitaResultado]
