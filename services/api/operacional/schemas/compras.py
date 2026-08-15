from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List, Literal
from datetime import datetime
import uuid


# ── Solicitação de Compra (Step 147) ──────────────────────────────────────────
# Uma solicitação pode pedir vários produtos (ver `itens`). Os campos escalares
# (produto_id/deposito_id/quantidade_solicitada/unidade) são um atalho legado
# para o caso de 1 item só — se `itens` não for enviado, viram automaticamente
# uma lista de 1 item.

class SolicitacaoItemCreate(BaseModel):
    produto_id: uuid.UUID
    deposito_id: uuid.UUID
    quantidade_solicitada: float = Field(..., gt=0)
    unidade: str = Field(..., max_length=20)


class SolicitacaoItemUpdate(BaseModel):
    quantidade_solicitada: float = Field(..., gt=0)


class SolicitacaoCompraCreate(BaseModel):
    itens: Optional[List[SolicitacaoItemCreate]] = Field(None, min_length=1)

    # Atalho legado para 1 item só (ver docstring acima).
    item_id: Optional[uuid.UUID] = Field(None, alias="produto_id")
    deposito_id: Optional[uuid.UUID] = None
    quantidade_solicitada: Optional[float] = Field(None, gt=0)
    unidade: Optional[str] = Field(None, max_length=20)

    origem: str = Field("MANUAL", description="REPOSICAO_ESTOQUE | MANUAL")
    origem_id: Optional[str] = Field(None, max_length=50)

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _normalizar_itens(self):
        if not self.itens:
            if not (self.item_id and self.deposito_id and self.quantidade_solicitada and self.unidade):
                raise ValueError("Informe 'itens' (lista) ou os campos produto_id/deposito_id/quantidade_solicitada/unidade.")
            self.itens = [SolicitacaoItemCreate(
                produto_id=self.item_id,
                deposito_id=self.deposito_id,
                quantidade_solicitada=self.quantidade_solicitada,
                unidade=self.unidade,
            )]
        return self


class FornecedorConsistenciaResponse(BaseModel):
    fornecedor_nome: str
    preco_medio: float
    desvio_padrao: float
    variacao_percentual: float
    classificacao: str


class SolicitacaoItemResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: Optional[str] = None
    deposito_id: uuid.UUID
    deposito_nome: Optional[str] = None
    quantidade_solicitada: float
    unidade: str
    quantidade_alocada: float = 0.0
    status_atendimento: Literal["PENDENTE", "PARCIAL", "ATENDIDO"] = "PENDENTE"
    valor_ultima_compra: Optional[float] = None
    data_ultima_compra: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SolicitacaoCompraResponse(BaseModel):
    id: uuid.UUID
    numero: Optional[str] = None
    tenant_id: uuid.UUID
    solicitante_id: Optional[uuid.UUID] = None
    solicitante_nome: Optional[str] = None
    itens: List[SolicitacaoItemResponse] = []

    # Atalho legado: espelha o primeiro item, para telas ainda não migradas.
    produto_id: Optional[uuid.UUID] = Field(None, serialization_alias="item_id")
    produto_nome: Optional[str] = None
    deposito_id: Optional[uuid.UUID] = None
    deposito_nome: Optional[str] = None
    quantidade_solicitada: Optional[float] = None
    unidade: Optional[str] = None

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
    quantidade_embalagens: Optional[int] = Field(
        None, ge=0, description="OPERATIONS-GAP-01 §21.20: nº de embalagens físicas recebidas, para logística reversa (Lei 9.974/2000)"
    )


class RecebimentoCreate(BaseModel):
    numero_nf: Optional[str] = Field(None, max_length=50)
    chave_nfe: Optional[str] = Field(None, max_length=60)
    observacoes: Optional[str] = Field(None, max_length=500)
    itens: Optional[List[ItemRecebimentoCreate]] = None


class EstornoRecebimentoRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


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
# Uma cotação pode cobrir vários itens da solicitação (ver `itens`). O atalho
# legado `valor_unitario` cota o item único de solicitações de 1 item só.

class CotacaoItemCreate(BaseModel):
    solicitacao_item_id: uuid.UUID
    valor_unitario: float = Field(..., gt=0)
    # Quantidade que o fornecedor efetivamente atende deste item — pode ser
    # menor que o solicitado (cotação parcial). Se omitido, assume o total
    # solicitado. Nunca pode superar Solicitacao Item.quantidade_solicitada.
    quantidade_atendida: Optional[float] = Field(None, gt=0)


class CotacaoSolicitacaoCreate(BaseModel):
    fornecedor_id: uuid.UUID
    condicoes_pagamento: Optional[str] = Field(None, max_length=100)
    prazo_entrega_dias: Optional[int] = Field(None, ge=0)

    itens: Optional[List[CotacaoItemCreate]] = Field(None, min_length=1)

    # Atalho legado: cota o item único da solicitação (só válido se ela tiver 1 item).
    valor_unitario: Optional[float] = Field(None, gt=0)
    quantidade_atendida: Optional[float] = Field(None, gt=0)


class CotacaoItemUpdate(BaseModel):
    valor_unitario: float = Field(..., gt=0)
    quantidade_atendida: Optional[float] = Field(None, gt=0)


class CotacaoUpdate(BaseModel):
    condicoes_pagamento: Optional[str] = Field(None, max_length=100)
    prazo_entrega_dias: Optional[int] = Field(None, ge=0)


class CotacaoItemResponse(BaseModel):
    id: uuid.UUID
    solicitacao_item_id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: Optional[str] = None
    quantidade: float
    valor_unitario: float
    valor_total: float
    # True quando já existe alocação deste item convertida em pedido — o
    # fornecedor "fechou" o que ofertou e não deve mais aparecer como opção
    # para alocar o saldo pendente do item da solicitação.
    tem_pedido_gerado: bool = False

    model_config = ConfigDict(from_attributes=True)


class CotacaoSolicitacaoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    numero: Optional[str] = None
    solicitacao_id: uuid.UUID
    itens: List[CotacaoItemResponse] = []
    fornecedor_id: Optional[uuid.UUID] = None
    fornecedor_nome: str
    fornecedor_contato: Optional[str]
    condicoes_pagamento: Optional[str] = None
    valor_unitario: Optional[float] = None
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


# ── Alocação item×fornecedor ───────────────────────────────────────────────────
# O comprador escolhe, por item da solicitação, quanto comprar de qual cotação
# (fornecedor) — pode dividir o mesmo item entre vários fornecedores/quantidades
# parciais. Ver ComprasService.alocar_itens / gerar_pedidos_de_alocacoes.

class AlocacaoItemCreate(BaseModel):
    solicitacao_item_id: uuid.UUID
    cotacao_item_id: uuid.UUID
    quantidade: float = Field(..., gt=0)


class AlocacaoRequest(BaseModel):
    itens: List[AlocacaoItemCreate] = Field(..., min_length=1)


# ── Pedido de Compra (Step 150) ────────────────────────────────────────────────
# Um pedido pode ter vários itens (ver `itens`, tabela compras_itens_pedido).
# Os campos escalares abaixo (item_id/quantidade/valor_unitario etc) espelham o
# primeiro item, mantidos para telas ainda não migradas.

class ItemPedidoResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: Optional[str] = None
    deposito_id: Optional[uuid.UUID] = None
    deposito_nome: Optional[str] = None
    quantidade_solicitada: float
    unidade: str
    preco_estimado_unitario: float
    valor_total: float
    quantidade_recebida: float
    status_item: str

    model_config = ConfigDict(from_attributes=True)


class PedidoCompraResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    numero: Optional[str] = None
    solicitacao_id: Optional[uuid.UUID] = None
    cotacao_id: Optional[uuid.UUID] = None

    fornecedor_id: Optional[uuid.UUID] = None
    fornecedor_nome: str
    fornecedor_contato: Optional[str] = None
    condicoes_pagamento: Optional[str] = None
    valor_adiantamento: Optional[float] = None

    itens: List[ItemPedidoResponse] = []

    # Campos de conveniência calculados a partir de `itens` (não persistidos em
    # colunas próprias) — só ficam preenchidos quando o pedido tem 1 item só;
    # em pedidos multi-item, a UI deve iterar `itens`.
    item_nome: Optional[str] = None
    deposito_id: Optional[uuid.UUID] = None
    deposito_nome: Optional[str] = None
    endereco_entrega: Optional[str] = None
    prazo_entrega_dias: Optional[int] = None

    quantidade: Optional[float] = None
    unidade: Optional[str] = None
    valor_unitario: Optional[float] = None
    valor_total: float

    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoCompraStatusUpdate(BaseModel):
    status: Literal["ABERTO", "ENVIADO", "RECEBIDO", "CANCELADO"]


class CondicoesPagamentoUpdate(BaseModel):
    condicoes_pagamento: str = Field(..., min_length=1, max_length=100)


class AdiantamentoUpdate(BaseModel):
    valor_adiantamento: float = Field(..., ge=0)


# ── Confirmação de Pedido pelo Fornecedor (link + senha por e-mail) ────────────

class ItemPedidoConfirmacaoPublica(BaseModel):
    produto_nome: str
    quantidade: float
    unidade: str
    preco_unitario: float
    valor_total: float


class PedidoConfirmacaoPublicaResponse(BaseModel):
    status: Literal["PENDENTE", "CONFIRMADO", "RECUSADO", "EXPIRADO"]
    fornecedor_nome: str
    tenant_nome: str
    itens: list[ItemPedidoConfirmacaoPublica]
    valor_total: float
    condicoes_pagamento: Optional[str] = None


class ConfirmacaoAceiteRequest(BaseModel):
    senha: str = Field(..., min_length=1, max_length=20)
    aceito: bool


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
