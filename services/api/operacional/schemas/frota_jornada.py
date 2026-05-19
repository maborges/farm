from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from operacional.schemas.frota_checklist import ChecklistOperacionalPreenchimentoCreate


StatusJornadaFrota = Literal["ABERTA", "FINALIZADA", "CANCELADA"]


class FrotaJornadaCreate(BaseModel):
    equipamento_id: UUID
    operador_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    safra_id: UUID | None = None
    talhao_id: UUID | None = None
    tipo_operacao: str = Field(min_length=2, max_length=80)
    data_inicio: datetime
    horimetro_inicial: float | None = None
    km_inicial: float | None = None
    observacoes: str | None = None
    checklist_abertura: ChecklistOperacionalPreenchimentoCreate | None = None
    aberta_por_id: UUID | None = None


class FrotaJornadaUpdate(BaseModel):
    operador_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    safra_id: UUID | None = None
    talhao_id: UUID | None = None
    tipo_operacao: str | None = Field(default=None, min_length=2, max_length=80)
    data_inicio: datetime | None = None
    horimetro_inicial: float | None = None
    km_inicial: float | None = None
    observacoes: str | None = None


class FrotaJornadaFinalizarRequest(BaseModel):
    data_fim: datetime
    horimetro_final: float | None = None
    km_final: float | None = None
    observacoes: str | None = None
    checklist_encerramento: ChecklistOperacionalPreenchimentoCreate | None = None
    encerrada_por_id: UUID | None = None


class FrotaJornadaCancelarRequest(BaseModel):
    observacoes: str | None = None


class FrotaJornadaResumo(BaseModel):
    total: int
    abertas: int
    finalizadas: int
    canceladas: int
    em_uso: int
    horas_trabalhadas: float
    km_trabalhados: float


class FrotaJornadaItem(BaseModel):
    id: UUID
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    operador_id: UUID | None = None
    operador_nome: str | None = None
    unidade_produtiva_id: UUID | None = None
    unidade_produtiva_nome: str | None = None
    safra_id: UUID | None = None
    safra_nome: str | None = None
    talhao_id: UUID | None = None
    talhao_nome: str | None = None
    tipo_operacao: str
    data_inicio: datetime
    data_fim: datetime | None = None
    horimetro_inicial: float | None = None
    horimetro_final: float | None = None
    km_inicial: float | None = None
    km_final: float | None = None
    status: StatusJornadaFrota
    observacoes: str | None = None
    aberta_por_id: UUID | None = None
    encerrada_por_id: UUID | None = None
    aberta_por_nome: str | None = None
    encerrada_por_nome: str | None = None
    duracao_horas: float | None = None
    horas_trabalhadas: float | None = None
    km_trabalhados: float | None = None
    custo_estimado: float | None = None
    metrica_custo: Literal["HORA", "KM", "INDISPONIVEL"] = "INDISPONIVEL"
    created_at: datetime
    updated_at: datetime


class FrotaJornadaListResponse(BaseModel):
    resumo: FrotaJornadaResumo
    jornadas: list[FrotaJornadaItem]
    gerado_em: datetime


class FrotaJornadaDetailResponse(BaseModel):
    jornada: FrotaJornadaItem
    gerado_em: datetime
