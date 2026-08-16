from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SistemaIrrigacaoCreate(BaseModel):
    imovel_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID | None = None
    nome: str = Field(..., max_length=150)
    tipo: str = Field(..., description="PIVO_CENTRAL | GOTEJAMENTO | ASPERSAO | MICROASPERSAO | SULCO | OUTRO")
    fonte_agua: str | None = Field(None, description="POCO | RIO | ACUDE | REDE_PUBLICA | ACUDE_PARTICULAR")
    area_irrigada_ha: Decimal | None = Field(None, ge=0)
    vazao_m3h: Decimal | None = Field(None, ge=0)
    pressao_bar: Decimal | None = Field(None, ge=0)
    potencia_motor_cv: Decimal | None = Field(None, ge=0)
    status: str = Field("ATIVO", description="ATIVO | INATIVO | MANUTENCAO")
    data_instalacao: date | None = None
    observacoes: str | None = None


class SistemaIrrigacaoUpdate(BaseModel):
    unidade_produtiva_id: uuid.UUID | None = None
    nome: str | None = Field(None, max_length=150)
    tipo: str | None = None
    fonte_agua: str | None = None
    area_irrigada_ha: Decimal | None = Field(None, ge=0)
    vazao_m3h: Decimal | None = Field(None, ge=0)
    pressao_bar: Decimal | None = Field(None, ge=0)
    potencia_motor_cv: Decimal | None = Field(None, ge=0)
    status: str | None = None
    data_instalacao: date | None = None
    observacoes: str | None = None


class SistemaIrrigacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    imovel_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID | None
    nome: str
    tipo: str
    fonte_agua: str | None
    area_irrigada_ha: Decimal | None
    vazao_m3h: Decimal | None
    pressao_bar: Decimal | None
    potencia_motor_cv: Decimal | None
    status: str
    data_instalacao: date | None
    observacoes: str | None
    created_at: datetime
    updated_at: datetime
