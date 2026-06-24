from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ManejoPlanejamentoAnimalItem(BaseModel):
    animal_id: UUID
    numero_brinco: str | None = None
    peso_kg: float | None = None
    observacao: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ManejoPlanejamentoLoteResumo(BaseModel):
    id: UUID
    identificacao: str

    model_config = ConfigDict(from_attributes=True)


class ManejoPlanejamentoOperadorResumo(BaseModel):
    id: UUID
    nome_exibicao: str

    model_config = ConfigDict(from_attributes=True)


class ManejoPlanejamentoCreate(BaseModel):
    tipo: Literal["PESAGEM", "VACINACAO"]
    lote_id: UUID
    animais_ids: list[UUID] = Field(default_factory=list)
    data_programada: date
    operador_id: UUID | None = None
    produto_id: UUID | None = None
    dose: float | None = None
    unidade_medida: str | None = None
    via_aplicacao: str | None = None
    observacoes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _validar_regras_por_tipo(self) -> "ManejoPlanejamentoCreate":
        if self.tipo == "VACINACAO":
            faltantes: list[str] = []
            if self.produto_id is None:
                faltantes.append("produto_id")
            if self.dose is None or self.dose <= 0:
                faltantes.append("dose")
            if not self.unidade_medida:
                faltantes.append("unidade_medida")
            if faltantes:
                faltas = ", ".join(faltantes)
                raise ValueError(f"Campos obrigatórios para VACINACAO ausentes: {faltas}.")
        return self


class ManejoPlanejamentoFiltro(BaseModel):
    tipo: str | None = None
    lote_id: UUID | None = None
    operador_id: UUID | None = None
    status: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    unidade_produtiva_id: UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ManejoPlanejamentoResponse(BaseModel):
    tarefa_campo_id: UUID
    tipo: Literal["PESAGEM", "VACINACAO"]
    lote: ManejoPlanejamentoLoteResumo
    area_id: UUID | None = None
    operador: ManejoPlanejamentoOperadorResumo | None = None
    status: str
    origem: str
    data_programada: date
    quantidade_animais: int
    observacoes: str | None = None
    animais: list[ManejoPlanejamentoAnimalItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ManejoPlanejamentoListResponse(BaseModel):
    items: list[ManejoPlanejamentoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
