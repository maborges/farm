from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

ModoGestaoLiteral = Literal["POR_LOTE", "INDIVIDUAL"]


class LoteBovinoCreate(BaseModel):
    unidade_produtiva_id: uuid.UUID
    piquete_id: Optional[uuid.UUID] = Field(
        None,
        validation_alias=AliasChoices("piquete_id", "area_id"),
    )
    identificacao: str = Field(..., min_length=2, max_length=100, description="Nome ou Número do Lote")
    modo_gestao: ModoGestaoLiteral = Field("POR_LOTE", description="POR_LOTE | INDIVIDUAL")
    categoria: str = Field(..., max_length=50, description="Ex: Bezerros, Vacas Paridas")
    raca: str = Field(..., max_length=50)
    quantidade_cabecas: int = Field(1, ge=0, description="Quantidade inicial de cabeças no lote")
    peso_medio_kg: float = Field(0.0, ge=0)
    peso_inicial_medio_kg: Optional[float] = Field(None, ge=0)
    rendimento_carcaca_pct: float = Field(50.0, ge=30.0, le=70.0)
    valor_aquisicao_total: Optional[float] = Field(None, ge=0)
    cotacao_arroba_override: Optional[float] = Field(None, gt=0)
    data_formacao: Optional[date] = None

    @model_validator(mode="after")
    def validar_quantidade_inicial(self) -> LoteBovinoCreate:
        """Exige ao menos uma cabeça na fundação de lotes geridos por saldo coletivo."""
        if self.modo_gestao == "POR_LOTE" and self.quantidade_cabecas < 1:
            raise ValueError("Lote no modo POR_LOTE precisa iniciar com pelo menos 1 cabeça.")
        return self


class LoteBovinoUpdate(BaseModel):
    piquete_id: Optional[uuid.UUID] = Field(
        None,
        validation_alias=AliasChoices("piquete_id", "area_id"),
    )
    identificacao: Optional[str] = Field(None, min_length=2, max_length=100)
    modo_gestao: Optional[ModoGestaoLiteral] = None
    categoria: Optional[str] = Field(None, max_length=50)
    raca: Optional[str] = Field(None, max_length=50)
    quantidade_cabecas: Optional[int] = Field(None, ge=0)
    peso_medio_kg: Optional[float] = Field(None, ge=0)
    peso_inicial_medio_kg: Optional[float] = Field(None, ge=0)
    rendimento_carcaca_pct: Optional[float] = Field(None, ge=30.0, le=70.0)
    valor_aquisicao_total: Optional[float] = Field(None, ge=0)
    cotacao_arroba_override: Optional[float] = Field(None, gt=0)
    ativo: Optional[bool] = None


class LoteBovinoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID
    piquete_id: Optional[uuid.UUID] = Field(None, validation_alias="area_id")
    identificacao: str
    modo_gestao: str = "POR_LOTE"
    categoria: Optional[str] = None
    raca: Optional[str] = None
    quantidade_cabecas: int
    peso_medio_kg: float
    peso_inicial_medio_kg: Optional[float] = None
    rendimento_carcaca_pct: float = 50.0
    valor_aquisicao_total: Optional[float] = None
    cotacao_arroba_override: Optional[float] = None
    data_formacao: date
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
