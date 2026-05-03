from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
import uuid


# ── Solicitação de Compra (Step 147) ──────────────────────────────────────────

class SolicitacaoCompraCreate(BaseModel):
    item_id: uuid.UUID = Field(..., alias="produto_id")
    deposito_id: uuid.UUID
    quantidade_solicitada: float = Field(..., gt=0)
    unidade: str = Field(..., max_length=20)
    origem: str = Field("MANUAL", description="REPOSICAO_ESTOQUE | MANUAL")
    origem_id: Optional[str] = Field(None, max_length=50)

    model_config = ConfigDict(populate_by_name=True)


class FornecedorConsistenciaResponse(BaseModel):
    fornecedor_nome: str
    preco_medio: float
    desvio_padrao: float
    variacao_percentual: float
    classificacao: str

class SolicitacaoCompraResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    produto_id: uuid.UUID = Field(..., serialization_alias="item_id")
    produto_nome: Optional[str] = None
    deposito_id: uuid.UUID
    deposito_nome: Optional[str] = None
    quantidade_solicitada: float
    unidade: str
    origem: str
    origem_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SolicitacaoCompraStatusUpdate(BaseModel):
    status: Literal["ABERTA", "EM_ANALISE", "APROVADA", "CANCELADA"]


# ── Recebimento Parcial ────────────────────────────────────────────────────────

class ItemRecebimentoCreate(BaseModel):
    item_pedido_id: uuid.UUID
    quantidade_recebida: float = Field(..., gt=0)
    preco_real_unitario: float = Field(0.0, ge=0)
    numero_lote_fornecedor: Optional[str] = Field(None, max_length=100, description="Supplier batch number")
    lote_id: Optional[uuid.UUID] = None


class RecebimentoCreate(BaseModel):
    numero_nf: Optional[str] = Field(None, max_length=50)
    chave_nfe: Optional[str] = Field(None, max_length=60)
    observacoes: Optional[str] = Field(None, max_length=500)
    itens: List[ItemRecebimentoCreate] = Field(..., min_length=1)


class ItemRecebimentoResponse(BaseModel):
    id: uuid.UUID
    item_pedido_id: uuid.UUID
    quantidade_recebida: float
    preco_real_unitario: float
    numero_lote_fornecedor: Optional[str]
    lote_id: Optional[uuid.UUID]
    model_config = ConfigDict(from_attributes=True)


class RecebimentoResponse(BaseModel):
    id: uuid.UUID
    pedido_id: uuid.UUID
    data_recebimento: datetime
    numero_nf: Optional[str]
    chave_nfe: Optional[str]
    observacoes: Optional[str]
    itens: List[ItemRecebimentoResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ── Devolução ao Fornecedor ────────────────────────────────────────────────────

class ItemDevolucaoCreate(BaseModel):
    produto_id: uuid.UUID
    deposito_origem_id: uuid.UUID
    quantidade: float = Field(..., gt=0)
    custo_unitario: float = Field(0.0, ge=0)
    lote_id: Optional[uuid.UUID] = None


class DevolucaoCreate(BaseModel):
    fornecedor_id: uuid.UUID
    pedido_id: Optional[uuid.UUID] = None
    motivo: str = Field(..., description="DEFEITO | QUANTIDADE_ERRADA | FORA_SPEC | VENCIDO | OUTRO")
    observacoes: Optional[str] = Field(None, max_length=500)
    itens: List[ItemDevolucaoCreate] = Field(..., min_length=1)


class DevolucaoStatusUpdate(BaseModel):
    status: str = Field(..., description="ENVIADA | CONCLUIDA | RECUSADA")
    numero_nf_devolucao: Optional[str] = Field(None, max_length=50)


class ItemDevolucaoResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    deposito_origem_id: uuid.UUID
    quantidade: float
    custo_unitario: float
    lote_id: Optional[uuid.UUID]
    model_config = ConfigDict(from_attributes=True)


class DevolucaoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    fornecedor_id: uuid.UUID
    pedido_id: Optional[uuid.UUID]
    data_devolucao: datetime
    motivo: str
    status: str
    numero_nf_devolucao: Optional[str]
    observacoes: Optional[str]
    itens: List[ItemDevolucaoResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ── Cotação de Preços (Step 149) ──────────────────────────────────────────────

class CotacaoSolicitacaoCreate(BaseModel):
    fornecedor_nome: str = Field(..., max_length=150)
    fornecedor_contato: Optional[str] = Field(None, max_length=150)
    valor_unitario: float = Field(..., gt=0)
    prazo_entrega_dias: Optional[int] = Field(None, ge=0)


class CotacaoSolicitacaoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    solicitacao_id: uuid.UUID
    fornecedor_nome: str
    fornecedor_contato: Optional[str]
    valor_unitario: float
    valor_total: float
    prazo_entrega_dias: Optional[int]
    status: str
    
    # Inteligência
    acima_media: bool = False
    percentual_acima_media: Optional[float] = None
    mensagem_alerta: Optional[str] = None
    
    # Step 159: Score de Compra
    score_compra: float = 0.0
    classificacao_score: str = "ATENCAO" # BOA, ATENCAO, RUIM
    motivos_score: List[str] = []
    
    # Step 160: Ranking
    posicao_ranking: int = 0
    melhor_opcao: bool = False
    
    # Step 161: Assistente de Compra (Exposição Textual)
    explicacao_compra: Optional[str] = None
    pontos_fortes: List[str] = []
    pontos_atencao: List[str] = []
    
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Pedido de Compra (Step 150) ────────────────────────────────────────────────

class PedidoCompraResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    solicitacao_id: Optional[uuid.UUID] = None
    cotacao_id: Optional[uuid.UUID] = None
    
    fornecedor_nome: str
    fornecedor_contato: Optional[str] = None
    
    item_id: uuid.UUID
    item_nome: Optional[str] = None
    deposito_id: uuid.UUID
    deposito_nome: Optional[str] = None
    
    quantidade: float
    unidade: str
    valor_unitario: float
    valor_total: float
    
    status: str
    data_pedido: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoCompraStatusUpdate(BaseModel):
    status: Literal["ABERTO", "ENVIADO", "RECEBIDO", "CANCELADO"]


# ── Inteligência de Compra (Step 153) ──────────────────────────────────────────

class PrecoHistoricoItem(BaseModel):
    fornecedor_nome: str
    valor_unitario: float
    data: datetime
    origem: str

class PrecoHistoricoResponse(BaseModel):
    menor_preco: float
    maior_preco: float
    preco_medio: float
    historico: List[PrecoHistoricoItem]

class PrecoIdealResponse(BaseModel):
    preco_minimo_referencia: float
    preco_ideal: float
    preco_maximo_recommended: float
    base_calculo: str

class MelhorFornecedorResponse(BaseModel):
    fornecedor_nome: str
    preco_medio: float
    ultimo_preco: float
    qtd_compras: int
    score: float

# ── Dashboard de Economia (Step 163) ──────────────────────────────────────────

class MelhorDecisaoItem(BaseModel):
    item: str
    economia: float

class EconomiaAnalyticsResponse(BaseModel):
    economia_total: float
    economia_media_percentual: float
    total_pedidos: int
    melhor_decisao: MelhorDecisaoItem

# ── Série Temporal de Economia (Step 164) ─────────────────────────────────────

class EconomiaSerieTemporalItem(BaseModel):
    periodo: str  # YYYY-MM
    economia_total: float

class EconomiaSerieTemporalResponse(BaseModel):
    items: list[EconomiaSerieTemporalItem]

class EconomiaCategoriaItem(BaseModel):
    categoria: str
    economia_total: float
    percentual: float

class EconomiaCategoriaResponse(BaseModel):
    items: list[EconomiaCategoriaItem]

# ── Performance de Compradores (Step 166) ────────────────────────────────────

class EconomiaUsuarioItem(BaseModel):
    usuario_id: Optional[uuid.UUID]
    usuario_nome: str
    economia_total: float
    economia_percentual: float
    total_pedidos: int

class EconomiaUsuarioResponse(BaseModel):
    items: list[EconomiaUsuarioItem]

# ── Performance por Fornecedor (Step 167) ────────────────────────────────────

class EconomiaFornecedorItem(BaseModel):
    fornecedor_nome: str
    economia_total: float
    economia_percentual: float
    total_pedidos: int

class EconomiaFornecedorResponse(BaseModel):
    items: list[EconomiaFornecedorItem]
