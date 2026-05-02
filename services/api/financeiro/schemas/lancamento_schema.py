from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
import uuid as _uuid

CATEGORIAS_VALIDAS = ("INSUMOS", "MAO_OBRA", "OPERACOES", "ADMINISTRATIVO")


class LancamentoCreate(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=200)
    valor: float = Field(..., gt=0)
    data: date
    safra_id: Optional[UUID] = None
    tipo: str = "CUSTO"
    categoria: str = "OPERACOES"

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in ("CUSTO", "RECEITA"):
            raise ValueError("tipo deve ser CUSTO ou RECEITA")
        return v

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in CATEGORIAS_VALIDAS:
            return "OPERACOES"
        return v


class LancamentoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    safra_id: Optional[UUID]
    descricao: str
    valor: float
    data: date
    tipo: str
    categoria: str
    created_at: datetime


class LancamentoResumo(BaseModel):
    total_custos: float
    total_receitas: float
    saldo: float
    quantidade: int


class CategoriaBreakdown(BaseModel):
    nome: str
    valor: float


class SerieTemporal(BaseModel):
    periodo: str
    total: float


class AlertaSafra(BaseModel):
    tipo: str   # CUSTO_REGISTRADO | MARGEM_NEGATIVA | AUMENTO_CUSTO
    nivel: str  # info | warning | danger
    mensagem: str


class RecomendacaoSafra(BaseModel):
    tipo: str       # REVISAR_CUSTOS | ANALISAR_INSUMOS | VER_EVOLUCAO
    mensagem: str
    acao: str       # texto curto do botão
    rota: str       # caminho de destino (ex: "/agricola/safras/{id}/cenarios")


class InsightDashboard(BaseModel):
    total_custos: float
    quantidade_lancamentos: int
    safra_id: Optional[UUID] = None
    safra_nome: Optional[str]
    cenario_custo_total: Optional[float]
    cenario_receita_total: Optional[float]
    cenario_margem: Optional[float]
    mensagem: Optional[str]
    categorias: List[CategoriaBreakdown] = []
