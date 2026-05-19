from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
import uuid


class ApontamentoUsoCreate(BaseModel):
    equipamento_id: uuid.UUID
    operador_id: Optional[uuid.UUID] = None
    jornada_id: Optional[uuid.UUID] = None
    data: datetime
    turno: str = "INTEGRAL"

    horimetro_inicio: float
    horimetro_fim: float
    km_inicio: Optional[float] = None
    km_fim: Optional[float] = None

    unidade_produtiva_id: Optional[uuid.UUID] = None
    safra_id: Optional[uuid.UUID] = None
    production_unit_id: Optional[uuid.UUID] = None
    talhao_id: Optional[uuid.UUID] = None
    operacao_id: Optional[uuid.UUID] = None
    area_ha_trabalhada: Optional[float] = None
    quantidade_produzida: Optional[float] = None
    quantidade_aplicada: Optional[float] = None
    custo_total: Optional[float] = None
    custo_por_ha: Optional[float] = None

    implementos_ids: Optional[list[uuid.UUID]] = None
    combustivel_consumido_l: Optional[float] = None
    observacoes: Optional[str] = None

    @model_validator(mode="after")
    def horimetro_fim_maior(self):
        if self.horimetro_fim < self.horimetro_inicio:
            raise ValueError("horimetro_fim deve ser >= horimetro_inicio")
        if self.area_ha_trabalhada is not None and self.area_ha_trabalhada < 0:
            raise ValueError("area_ha_trabalhada deve ser >= 0")
        if self.quantidade_produzida is not None and self.quantidade_produzida < 0:
            raise ValueError("quantidade_produzida deve ser >= 0")
        if self.quantidade_aplicada is not None and self.quantidade_aplicada < 0:
            raise ValueError("quantidade_aplicada deve ser >= 0")
        if self.custo_total is not None and self.custo_total < 0:
            raise ValueError("custo_total deve ser >= 0")
        if self.custo_por_ha is not None and self.custo_por_ha < 0:
            raise ValueError("custo_por_ha deve ser >= 0")
        return self


class ApontamentoUsoUpdate(BaseModel):
    operador_id: Optional[uuid.UUID] = None
    jornada_id: Optional[uuid.UUID] = None
    turno: Optional[str] = None
    horimetro_inicio: Optional[float] = None
    horimetro_fim: Optional[float] = None
    km_inicio: Optional[float] = None
    km_fim: Optional[float] = None
    unidade_produtiva_id: Optional[uuid.UUID] = None
    safra_id: Optional[uuid.UUID] = None
    production_unit_id: Optional[uuid.UUID] = None
    talhao_id: Optional[uuid.UUID] = None
    operacao_id: Optional[uuid.UUID] = None
    area_ha_trabalhada: Optional[float] = None
    quantidade_produzida: Optional[float] = None
    quantidade_aplicada: Optional[float] = None
    custo_total: Optional[float] = None
    custo_por_ha: Optional[float] = None
    implementos_ids: Optional[list[uuid.UUID]] = None
    combustivel_consumido_l: Optional[float] = None
    observacoes: Optional[str] = None


class ApontamentoUsoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    equipamento_id: uuid.UUID
    jornada_id: Optional[uuid.UUID]
    operador_id: Optional[uuid.UUID]
    data: datetime
    turno: str
    horimetro_inicio: float
    horimetro_fim: float
    horas_trabalhadas: float = 0.0
    km_inicio: Optional[float]
    km_fim: Optional[float]
    unidade_produtiva_id: Optional[uuid.UUID]
    safra_id: Optional[uuid.UUID]
    production_unit_id: Optional[uuid.UUID]
    talhao_id: Optional[uuid.UUID]
    operacao_id: Optional[uuid.UUID]
    area_ha_trabalhada: Optional[float]
    quantidade_produzida: Optional[float]
    quantidade_aplicada: Optional[float]
    custo_total: Optional[float]
    custo_por_ha: Optional[float]
    implementos_ids: Optional[list]
    combustivel_consumido_l: Optional[float]
    observacoes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def calc_horas(self):
        self.horas_trabalhadas = round(self.horimetro_fim - self.horimetro_inicio, 2)
        return self
