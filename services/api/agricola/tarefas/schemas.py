from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime, date
from typing import Optional


class TarefaCreate(BaseModel):
    talhao_id: Optional[UUID] = None
    talhoes_ids: Optional[list[UUID]] = Field(
        None, description="Alternativa a talhao_id: gera 1 SafraTarefa por talhão (fan-out), unidas por grupo_geracao_id"
    )
    production_unit_id: Optional[UUID] = None
    cultivo_area_id: Optional[UUID] = None
    analise_solo_id: Optional[UUID] = None
    grupo_geracao_id: Optional[UUID] = Field(
        None, description="Marca tarefas nascidas juntas na mesma ação de geração em lote"
    )
    origem: str = "MANUAL"
    tipo: str = Field(..., description="CALAGEM|ADUBACAO_FOSFORO|ADUBACAO_POTASSIO|ADUBACAO_NITROGENIO|GRADAGEM|PLANTIO|PULVERIZACAO|IRRIGACAO|COLHEITA|OUTRO")
    fase: Optional[str] = Field(None, description="Fase da safra")
    criticidade: str = Field("NORMAL", description="CRITICA|NORMAL|OPCIONAL")
    descricao: str = Field(..., min_length=3, max_length=300)
    obs: Optional[str] = None
    prioridade: str = "MEDIA"
    dose_estimada_kg_ha: Optional[float] = None
    quantidade_total_estimada_kg: Optional[float] = None
    area_ha: Optional[float] = None
    custo_estimado: Optional[float] = None
    data_prevista: Optional[date] = None


class TarefaUpdate(BaseModel):
    fase: Optional[str] = None
    criticidade: Optional[str] = None
    descricao: Optional[str] = Field(None, min_length=3, max_length=300)
    obs: Optional[str] = None
    prioridade: Optional[str] = None
    talhao_id: Optional[UUID] = None
    production_unit_id: Optional[UUID] = None
    tipo: Optional[str] = None
    custo_estimado: Optional[float] = None
    data_prevista: Optional[date] = None


class TarefaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    safra_id: UUID
    talhao_id: Optional[UUID]
    production_unit_id: Optional[UUID]
    cultivo_area_id: Optional[UUID]
    analise_solo_id: Optional[UUID]
    grupo_geracao_id: Optional[UUID]
    origem: str
    tipo: str
    fase: Optional[str]
    criticidade: str
    descricao: str
    obs: Optional[str]
    prioridade: str
    status: str
    dose_estimada_kg_ha: Optional[float]
    quantidade_total_estimada_kg: Optional[float]
    area_ha: Optional[float]
    custo_estimado: Optional[float]
    data_prevista: Optional[date]
    aprovado_por: Optional[UUID]
    aprovado_em: Optional[datetime]
    operacao_id: Optional[UUID]
    concluida_em: Optional[datetime]
    cancelado_por: Optional[UUID]
    cancelado_em: Optional[datetime]
    motivo_cancelamento: Optional[str]
    invalidado_por: Optional[UUID]
    invalidado_em: Optional[datetime]
    motivo_invalidacao: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class PlanejarInsumoRequest(BaseModel):
    produto_id: UUID
    dose_por_ha: float = Field(..., gt=0)
    unidade: str = Field(..., min_length=1, max_length=20)


class PlanejarOperacaoRequest(BaseModel):
    data_prevista: date
    operador_id: Optional[UUID] = None
    maquina_id: Optional[UUID] = None
    implemento_id: Optional[UUID] = None
    insumos: list[PlanejarInsumoRequest] = []


class SafraTarefaNecessidadeCreate(BaseModel):
    categoria: str = Field(..., description="CORRETIVO|FERTILIZANTE|DEFENSIVO|SEMENTE|COMBUSTIVEL|OUTRO")
    tipo_aplicacao: Optional[str] = None
    unidade_referencia: str = Field(..., min_length=1, max_length=20)
    unidade_medida_id: Optional[UUID] = None
    dose_tecnica: Optional[float] = None
    quantidade_tecnica: Optional[float] = None
    area_referencia_ha: Optional[float] = None
    origem_calculo: str = "MANUAL"
    parametros_calculo: Optional[dict] = None


class SafraTarefaNecessidadeUpdate(BaseModel):
    categoria: Optional[str] = None
    tipo_aplicacao: Optional[str] = None
    unidade_referencia: Optional[str] = None
    unidade_medida_id: Optional[UUID] = None
    dose_tecnica: Optional[float] = None
    quantidade_tecnica: Optional[float] = None
    area_referencia_ha: Optional[float] = None
    parametros_calculo: Optional[dict] = None


class SafraTarefaNecessidadeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    safra_tarefa_id: UUID
    categoria: str
    tipo_aplicacao: Optional[str]
    unidade_referencia: str
    unidade_medida_id: Optional[UUID]
    dose_tecnica: Optional[float]
    quantidade_tecnica: Optional[float]
    area_referencia_ha: Optional[float]
    origem_calculo: str
    parametros_calculo: Optional[dict]
    created_at: datetime
    updated_at: datetime
