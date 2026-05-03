from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
import uuid as _uuid

CATEGORIAS_VALIDAS = ("INSUMOS", "MAO_OBRA", "OPERACOES", "ADMINISTRATIVO")


class LancamentoCreate(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=200)
    valor: float = Field(..., gt=0, description="Valor deve ser maior que zero")
    data: date
    safra_id: Optional[UUID] = None
    tipo: str = "CUSTO"
    categoria: str = "OPERACOES"
    origem: Optional[str] = None
    origem_id: Optional[UUID] = None

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
            raise ValueError(
                f"Categoria inválida. Valores aceitos: {', '.join(CATEGORIAS_VALIDAS)}"
            )
        return v

    @field_validator("origem")
    @classmethod
    def validar_origem(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.upper().strip()
        return v


class LancamentoUpdate(BaseModel):
    descricao: Optional[str] = Field(None, min_length=1, max_length=200)
    valor: Optional[float] = Field(None, gt=0)
    data: Optional[date] = None
    categoria: Optional[str] = None

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.upper().strip()
        if v not in CATEGORIAS_VALIDAS:
            raise ValueError(
                f"Categoria inválida. Valores aceitos: {', '.join(CATEGORIAS_VALIDAS)}"
            )
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
    origem: Optional[str] = None
    origem_id: Optional[UUID] = None
    created_at: datetime

    @property
    def gerado_automaticamente(self) -> bool:
        return self.origem is not None


class LancamentoOrigemItem(BaseModel):
    model_config = {"from_attributes": True}

    lancamento_id: UUID
    descricao: str
    valor: float
    origem: str
    origem_id: Optional[UUID]
    data: date
    categoria: str
    gerado_automaticamente: bool


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


class ItemPlanoAcao(BaseModel):
    id: str
    tipo: str
    titulo: str
    descricao: str
    prioridade: str   # ALTA | MEDIA | BAIXA
    status: str = "PENDENTE"
    rota: str


class ResumoInteligente(BaseModel):
    titulo: str
    resumo: str
    pontos_atencao: List[str] = []
    proximas_acoes: List[str] = []


class ResumoConsultivoResponse(BaseModel):
    titulo: str
    resumo: str
    recomendacoes: List[str] = []
    pontos_atencao: List[str] = []
    nivel_confianca: str = "ALTO"
    fonte: str = "DETERMINISTICO"
    ia_disponivel: bool = False
    limite_atingido: bool = False


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
