from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID
from datetime import date, time, datetime
from typing import Optional, List

class InsumoOperacaoCreate(BaseModel):
    produto_id: UUID
    lote_insumo: str | None = None
    lote_estoque_id: UUID | None = None
    unidade_medida_id: UUID | None = None
    dose_por_ha: float = Field(..., gt=0)
    unidade: str = Field(..., min_length=1, max_length=20)
    area_aplicada: float | None = None

    @field_validator("area_aplicada", mode="before")
    @classmethod
    def _blank_area_aplicada_to_none(cls, value):
        return None if value == "" else value

class InsumoOperacaoResponse(BaseModel):
    id: UUID
    produto_id: UUID
    lote_insumo: str | None
    lote_estoque_id: UUID | None
    unidade_medida_id: UUID | None
    dose_por_ha: float
    unidade: str
    area_aplicada: float | None
    quantidade_total: float | None
    custo_unitario: float | None
    custo_total: float | None
    carencia_dias: int | None
    data_reentrada: date | None
    epi_necessario: list[str] | None

    model_config = ConfigDict(from_attributes=True)

class OperacaoAgricolaCreate(BaseModel):
    safra_id: UUID
    talhao_id: UUID
    cultivo_id: UUID | None = None
    production_unit_id: UUID | None = None
    tarefa_id: UUID | None = None
    tipo: str
    subtipo: str | None = None
    descricao: str = Field(..., min_length=3, max_length=500)
    fase_safra: str | None = None  # None = auto-preenche com fase atual da safra
    data_prevista: date | None = None
    data_realizada: date
    hora_inicio: time | None = None
    hora_fim: time | None = None
    area_aplicada_ha: float = Field(..., gt=0)
    maquina_id: UUID | None = None
    implemento: str | None = None
    operador_id: UUID | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    custo_total: float | None = Field(None, ge=0)
    status: str = Field(default="REALIZADA", min_length=1, max_length=20)
    observacoes: str | None = None
    insumos: list[InsumoOperacaoCreate] = []

    @field_validator(
        "area_aplicada_ha",
        "latitude",
        "longitude",
        "custo_total",
        mode="before",
    )
    @classmethod
    def _blank_numeric_to_none(cls, value):
        return None if value == "" else value

class OperacaoAgricolaUpdate(BaseModel):
    cultivo_id: UUID | None = None
    tipo: str | None = None
    subtipo: str | None = None
    descricao: str | None = Field(None, min_length=3, max_length=500)
    fase_safra: str | None = None
    data_prevista: date | None = None
    data_realizada: date | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None
    area_aplicada_ha: float | None = Field(None, gt=0)
    maquina_id: UUID | None = None
    implemento: str | None = None
    operador_id: UUID | None = None
    production_unit_id: UUID | None = None
    custo_total: float | None = Field(None, ge=0)
    status: str | None = None
    observacoes: str | None = None
    insumos: list[InsumoOperacaoCreate] | None = None

    @field_validator(
        "area_aplicada_ha",
        "custo_total",
        mode="before",
    )
    @classmethod
    def _blank_numeric_to_none(cls, value):
        return None if value == "" else value


class OperacaoPorFaseKPI(BaseModel):
    fase: str
    total_operacoes: int
    custo_total: float
    custo_por_ha: float
    area_total_ha: float


class SafraOperacoesPorFaseResponse(BaseModel):
    safra_id: UUID
    fases: list[OperacaoPorFaseKPI]
    custo_total_safra: float


class OperacaoTipoFaseBase(BaseModel):
    tipo_operacao: str = Field(..., min_length=2, max_length=30)
    fases_permitidas: list[str] = Field(..., min_length=1)
    descricao: str | None = None


class OperacaoTipoFaseCreate(OperacaoTipoFaseBase):
    pass


class OperacaoTipoFaseUpdate(BaseModel):
    tipo_operacao: str | None = Field(None, min_length=2, max_length=30)
    fases_permitidas: list[str] | None = None
    descricao: str | None = None


class OperacaoTipoFaseResponse(OperacaoTipoFaseBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OperacaoAgricolaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    safra_id: UUID
    talhao_id: UUID
    cultivo_id: UUID | None
    talhao_nome: str | None = None
    production_unit_id: UUID | None = None
    tarefa_id: UUID | None = None
    tipo: str
    subtipo: str | None
    descricao: str
    data_prevista: date | None
    data_realizada: date
    hora_inicio: time | None
    hora_fim: time | None
    area_aplicada_ha: float | None
    maquina_id: UUID | None
    implemento: str | None
    operador_id: UUID | None
    temperatura_c: float | None
    umidade_rel: float | None
    vento_kmh: float | None
    direcao_vento: str | None
    condicao_clima: str | None
    latitude: float | None
    longitude: float | None
    fase_safra: str | None
    custo_total: float
    custo_por_ha: float
    origem_invalidada: bool = False
    origem_invalidada_em: datetime | None = None
    origem_invalidada_por: UUID | None = None
    motivo_invalidacao_origem: str | None = None
    documental_status: str | None = None
    status: str
    observacoes: str | None
    fotos: list[str]
    created_at: datetime
    updated_at: datetime
    insumos: list[InsumoOperacaoResponse]

    model_config = ConfigDict(from_attributes=True)
