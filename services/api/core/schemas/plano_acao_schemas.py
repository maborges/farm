from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

StatusPlanoAcao = Literal["ABERTO", "EM_ANDAMENTO", "CONCLUIDO", "ATRASADO"]


class PlanoAcaoViabilidadeResumo(BaseModel):
    """Resumo calculado de viabilidade econômica para planos de ação com CapEx."""

    vpl: float
    tir_aa: Optional[float] = None
    payback_simples_anos: Optional[float] = None
    payback_descontado_anos: Optional[float] = None
    veredito_final: Literal["VIAVEL", "INVIAVEL", "ATENCAO_LIQUIDEZ"]
    resumo_executivo: str


class PlanoAcaoCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    descricao: Optional[str] = None
    origem_indicador: Optional[str] = Field(None, max_length=100)
    unidade_produtiva_id: Optional[UUID] = None
    safra_id: Optional[UUID] = None
    tarefa_id: Optional[UUID] = None
    responsavel_id: Optional[UUID] = None
    responsavel_nome: Optional[str] = Field(None, max_length=150)
    meta: Optional[str] = Field(None, max_length=255)
    prazo: Optional[date] = None
    investimento_estimado: Optional[float] = Field(None, gt=0)
    retorno_anual_estimado: Optional[float] = Field(None, gt=0)
    horizonte_anos: Optional[int] = Field(None, ge=1, le=25)
    tma_aa: Optional[float] = Field(None, ge=0, le=200)
    prazo_maximo_payback_anos: Optional[float] = Field(None, gt=0)


class PlanoAcaoUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3, max_length=200)
    descricao: Optional[str] = None
    responsavel_id: Optional[UUID] = None
    responsavel_nome: Optional[str] = Field(None, max_length=150)
    meta: Optional[str] = Field(None, max_length=255)
    prazo: Optional[date] = None
    status: Optional[StatusPlanoAcao] = None
    resultado_obtido: Optional[str] = None
    investimento_estimado: Optional[float] = Field(None, gt=0)
    retorno_anual_estimado: Optional[float] = Field(None, gt=0)
    horizonte_anos: Optional[int] = Field(None, ge=1, le=25)
    tma_aa: Optional[float] = Field(None, ge=0, le=200)
    prazo_maximo_payback_anos: Optional[float] = Field(None, gt=0)


class PlanoAcaoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    unidade_produtiva_id: Optional[UUID] = None
    safra_id: Optional[UUID] = None
    tarefa_id: Optional[UUID] = None
    responsavel_id: Optional[UUID] = None
    titulo: str
    descricao: Optional[str] = None
    origem_indicador: Optional[str] = None
    responsavel_nome: Optional[str] = None
    meta: Optional[str] = None
    prazo: Optional[date] = None
    status: str
    resultado_obtido: Optional[str] = None
    concluido_em: Optional[datetime] = None
    investimento_estimado: Optional[float] = None
    retorno_anual_estimado: Optional[float] = None
    horizonte_anos: Optional[int] = None
    tma_aa: Optional[float] = None
    prazo_maximo_payback_anos: Optional[float] = None
    viabilidade: Optional[PlanoAcaoViabilidadeResumo] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
