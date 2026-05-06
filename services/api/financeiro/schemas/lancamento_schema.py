from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date, datetime
from typing import Optional, List, Any, Dict
from uuid import UUID
import uuid as _uuid

CATEGORIAS_CUSTO = ("INSUMOS", "MAO_OBRA", "OPERACOES", "ADMINISTRATIVO")
CATEGORIAS_RECEITA = ("VENDA_PRODUCAO", "OUTRAS_RECEITAS")


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

    @model_validator(mode="after")
    def validar_categoria_por_tipo(self) -> "LancamentoCreate":
        self.categoria = self.categoria.upper().strip()
        if self.tipo == "CUSTO":
            if self.categoria not in CATEGORIAS_CUSTO:
                raise ValueError(
                    f"Categoria inválida para CUSTO. Valores aceitos: {', '.join(CATEGORIAS_CUSTO)}"
                )
        else:  # RECEITA
            if self.categoria not in CATEGORIAS_RECEITA:
                raise ValueError(
                    f"Categoria inválida para RECEITA. Valores aceitos: {', '.join(CATEGORIAS_RECEITA)}"
                )
        return self

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
        todas = CATEGORIAS_CUSTO + CATEGORIAS_RECEITA
        if v not in todas:
            raise ValueError(
                f"Categoria inválida. Valores aceitos: {', '.join(todas)}"
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
    updated_at: datetime

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
    quantidade_lancamentos: int


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


class DREOperacional(BaseModel):
    receita_bruta: float
    custos_operacionais: float
    resultado_operacional: float
    margem_percentual: float
    breakdown_custos: List[CategoriaBreakdown] = []
    breakdown_receitas: List[CategoriaBreakdown] = []


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


class SimulacaoAjustes(BaseModel):
    receita_percentual: float = Field(0.0, description="Variação percentual na receita (ex: 10 para +10%)")
    custos_percentual: float = Field(0.0, description="Variação percentual nos custos (ex: -5 para -5%)")


class SimulacaoDREPayload(BaseModel):
    safra_id: UUID
    ajustes: SimulacaoAjustes


class SimulacaoDREResponse(BaseModel):
    receita_real: float
    custos_real: float
    resultado_real: float
    margem_real: float
    
    receita_simulada: float
    custos_simulados: float
    resultado_simulado: float
    margem_simulada: float
    
    variacao_resultado: float
    variacao_resultado_percentual: float


class MelhorDecisao(BaseModel):
    safra: str
    ganho: float


class PerformanceUsuarioResponse(BaseModel):
    total_decisoes: int
    economia_total: float
    melhor_decisao: MelhorDecisao
    taxa_sucesso: float
    ranking: str
    nivel: str


class SugestaoAcaoIA(BaseModel):
    acao: str # SIMULACAO | AJUSTE_CENARIO | ANALISE_DETALHADA
    parametros: Dict[str, Any]
    descricao: str


class AlertaInteligente(BaseModel):
    id: str
    tipo: str
    gravidade: str  # baixa, media, alta
    titulo: str
    mensagem: str
    impacto: str
    recomendacao: str
    acao: Optional[str] = None
    parametros: Optional[Dict[str, Any]] = None
    prioridade: float = 0.0 # Step 197
    motivo_prioridade: Optional[str] = None # Step 197
    acao_sugerida: Optional[SugestaoAcaoIA] = None # Step 200


class SaudeFinanceiraResumo(BaseModel):
    receita: float
    custos: float
    margem: float


class ResumoDiarioResponse(BaseModel):
    texto_resumo: str
    top_alertas: List[AlertaInteligente]
    saude_financeira: SaudeFinanceiraResumo
    risco_principal: str
    oportunidade_principal: str
    recomendacao_ia: str
    ia_disponivel: bool = False
    acao_sugerida: Optional[SugestaoAcaoIA] = None # Step 200
