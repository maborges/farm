from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional, List
from datetime import datetime, date
import uuid

TipoDeposito = Literal["GERAL", "COMBUSTIVEL", "DEFENSIVOS", "PECAS", "GRAOS", "OUTROS"]
StatusLote = Literal["ATIVO", "VENCIDO", "ESGOTADO", "BLOQUEADO"]


# ── Lote ──────────────────────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    produto_id: uuid.UUID
    deposito_id: uuid.UUID
    numero_lote: str = Field(..., min_length=1, max_length=100)
    data_fabricacao: Optional[date] = None
    data_validade: Optional[date] = None
    quantidade_inicial: float = Field(..., gt=0)
    custo_unitario: float = Field(0.0, ge=0)
    nota_fiscal_ref: Optional[str] = Field(None, max_length=100)
    qualidade_laudo_id: Optional[uuid.UUID] = None
    qualidade_status: Optional[str] = None
    peso_desconto_qualidade_kg: float = Field(0.0, ge=0)
    metadata_json: Optional[dict] = None


class LoteUpdate(BaseModel):
    data_validade: Optional[date] = None
    nota_fiscal_ref: Optional[str] = Field(None, max_length=100)
    status: Optional[StatusLote] = None


class LoteResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    deposito_id: uuid.UUID
    numero_lote: str
    data_fabricacao: Optional[date]
    data_validade: Optional[date]
    quantidade_inicial: float
    quantidade_atual: float
    custo_unitario: float
    nota_fiscal_ref: Optional[str]
    qualidade_laudo_id: Optional[uuid.UUID] = None
    qualidade_status: Optional[str] = None
    peso_desconto_qualidade_kg: float = 0.0
    metadata_json: Optional[dict] = None
    status: str
    created_at: datetime
    # True quando o lote foi zerado por um estorno de recebimento (não por
    # consumo normal) — ver ComprasService.estornar_recebimento.
    esgotado_por_estorno: bool = False
    model_config = ConfigDict(from_attributes=True)
TipoMovimentacao = Literal["ENTRADA", "SAIDA", "TRANSFERENCIA", "AJUSTE"]


# ── Depósito ──────────────────────────────────────────────────────────────────

class DepositoCreate(BaseModel):
    unidade_produtiva_id: uuid.UUID
    nome: str = Field(..., min_length=2, max_length=100)
    tipo: TipoDeposito = "GERAL"
    localizacao_desc: Optional[str] = Field(None, max_length=200)


class DepositoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    tipo: Optional[TipoDeposito] = None
    localizacao_desc: Optional[str] = None
    ativo: Optional[bool] = None


class DepositoResponse(BaseModel):
    id: uuid.UUID
    unidade_produtiva_id: uuid.UUID
    nome: str
    tipo: str
    localizacao_desc: Optional[str]
    ativo: bool
    model_config = ConfigDict(from_attributes=True)


# ── Saldo ─────────────────────────────────────────────────────────────────────

class SaldoResponse(BaseModel):
    id: uuid.UUID
    deposito_id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: str
    deposito_nome: str
    quantidade_atual: float
    quantidade_reservada: float = 0.0
    quantidade_disponivel: float = 0.0
    unidade_medida: str
    preco_medio: float = 0.0
    estoque_minimo: Optional[float] = None
    estoque_maximo: Optional[float] = None
    abaixo_minimo: bool
    acima_maximo: bool = False
    ultima_atualizacao: datetime
    model_config = ConfigDict(from_attributes=True)


class SaldoMinimoUpdateRequest(BaseModel):
    deposito_id: uuid.UUID
    estoque_minimo: float = Field(..., ge=0)


class SaldoMaximoUpdateRequest(BaseModel):
    deposito_id: uuid.UUID
    estoque_maximo: float = Field(..., ge=0)


# ── Localização física ──────────────────────────────────────────────────────

class EstoqueLocalizacaoCreate(BaseModel):
    deposito_id: uuid.UUID
    produto_id: uuid.UUID
    corredor: Optional[str] = Field(None, max_length=20)
    prateleira: Optional[str] = Field(None, max_length=20)
    posicao: Optional[str] = Field(None, max_length=20)
    codigo_localizacao: Optional[str] = Field(None, max_length=50)
    observacao_livre: Optional[str] = Field(None, max_length=200)
    quantidade: float = Field(0.0, ge=0)


class EstoqueLocalizacaoUpdate(BaseModel):
    corredor: Optional[str] = Field(None, max_length=20)
    prateleira: Optional[str] = Field(None, max_length=20)
    posicao: Optional[str] = Field(None, max_length=20)
    codigo_localizacao: Optional[str] = Field(None, max_length=50)
    observacao_livre: Optional[str] = Field(None, max_length=200)
    quantidade: Optional[float] = Field(None, ge=0)


class EstoqueLocalizacaoResponse(BaseModel):
    id: uuid.UUID
    deposito_id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: Optional[str] = None
    deposito_nome: Optional[str] = None
    corredor: Optional[str]
    prateleira: Optional[str]
    posicao: Optional[str]
    codigo_localizacao: Optional[str]
    observacao_livre: Optional[str]
    quantidade: float
    model_config = ConfigDict(from_attributes=True)


# ── Movimentações ─────────────────────────────────────────────────────────────

class EntradaEstoqueRequest(BaseModel):
    deposito_id: uuid.UUID
    produto_id: uuid.UUID
    fornecedor_id: uuid.UUID
    quantidade: float = Field(..., gt=0)
    custo_unitario: float = Field(0.0, ge=0)
    motivo: Optional[str] = Field(None, max_length=255)
    origem_id: Optional[uuid.UUID] = None
    origem_tipo: Optional[str] = Field(None, max_length=50, description="PEDIDO_COMPRA | AJUSTE | INICIAL")
    lote_id: Optional[uuid.UUID] = None


class SaidaEstoqueRequest(BaseModel):
    deposito_id: Optional[uuid.UUID] = None  # None = busca automática por fazenda
    unidade_produtiva_id: Optional[uuid.UUID] = None
    produto_id: uuid.UUID
    quantidade: float = Field(..., gt=0)
    motivo: Optional[str] = Field(None, max_length=255)
    origem_id: Optional[uuid.UUID] = None
    origem_tipo: Optional[str] = Field(None, max_length=50)
    lote_id: Optional[uuid.UUID] = None  # Se informado, desconta do lote específico (PEPS por padrão)
    safra_id: Optional[uuid.UUID] = None  # Quando informado, gera lançamento financeiro automático


class AjusteEstoqueRequest(BaseModel):
    deposito_id: uuid.UUID
    produto_id: uuid.UUID
    quantidade_nova: float = Field(..., ge=0, description="Quantidade correta após inventário")
    motivo: str = Field(..., min_length=3, max_length=255)
    # OPERATIONS-GAP-01 §21.13: antes só existia "AJUSTE" genérico, sem distinguir
    # perda física (quebra/deterioração) de contagem de inventário ou correção de
    # lançamento — impossibilitando relatório de perdas. Default preserva o
    # comportamento anterior (toda origem seguia como "AJUSTE").
    categoria_ajuste: Literal["CONTAGEM_INVENTARIO", "PERDA", "CORRECAO_LANCAMENTO"] = "CONTAGEM_INVENTARIO"


class AjusteMovimentoRequest(BaseModel):
    tipo_ajuste: Literal["ENTRADA", "SAIDA"]
    quantidade: float = Field(..., gt=0)
    motivo: str = Field(..., min_length=3, max_length=255)


class TransferenciaEstoqueRequest(BaseModel):
    deposito_origem_id: uuid.UUID
    deposito_destino_id: uuid.UUID
    produto_id: uuid.UUID
    quantidade: float = Field(..., gt=0)
    motivo: Optional[str] = None


class MovimentacaoResponse(BaseModel):
    id: uuid.UUID
    deposito_id: uuid.UUID
    deposito_nome: Optional[str] = None
    produto_id: uuid.UUID
    produto_nome: Optional[str] = None
    lote_id: Optional[uuid.UUID]
    tipo: str
    quantidade: float
    custo_unitario: Optional[float]
    custo_total: Optional[float]
    motivo: Optional[str]
    origem_id: Optional[uuid.UUID]
    origem_tipo: Optional[str]
    fornecedor_id: Optional[uuid.UUID] = None
    data_movimentacao: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Requisição Interna ────────────────────────────────────────────────────────

class ItemRequisicaoCreate(BaseModel):
    produto_id: uuid.UUID
    quantidade_solicitada: float = Field(..., gt=0)
    deposito_id: Optional[uuid.UUID] = None
    observacoes: Optional[str] = Field(None, max_length=255)


class RequisicaoCreate(BaseModel):
    unidade_produtiva_id: uuid.UUID
    data_necessidade: Optional[date] = None
    origem_tipo: str = Field("OUTRO", description="ORDEM_SERVICO | MANUTENCAO | PRODUCAO | OUTRO")
    origem_id: Optional[uuid.UUID] = None
    observacoes: Optional[str] = Field(None, max_length=500)
    itens: List[ItemRequisicaoCreate] = Field(..., min_length=1)


class ItemAprovacaoUpdate(BaseModel):
    item_id: uuid.UUID
    quantidade_aprovada: float = Field(..., ge=0)
    deposito_id: Optional[uuid.UUID] = None


class RequisicaoAprovarRequest(BaseModel):
    itens: List[ItemAprovacaoUpdate]


class ItemEntregaUpdate(BaseModel):
    item_id: uuid.UUID
    quantidade_entregue: float = Field(..., ge=0)
    lote_id: Optional[uuid.UUID] = None


class RequisicaoEntregarRequest(BaseModel):
    itens: List[ItemEntregaUpdate]


class ItemConferidoUpdate(BaseModel):
    item_id: uuid.UUID
    quantidade_conferida: float = Field(..., ge=0)


class ConfirmarRetiradaRequest(BaseModel):
    itens: List[ItemConferidoUpdate] = Field(..., min_length=1)
    email: str = Field(..., description="E-mail de quem está retirando — pode diferir do usuário logado")
    senha: str = Field(..., min_length=1)


class ItemDevolvidoUpdate(BaseModel):
    item_id: uuid.UUID
    quantidade_devolvida: float = Field(..., gt=0)


class ConfirmarDevolucaoRequest(BaseModel):
    itens: List[ItemDevolvidoUpdate] = Field(..., min_length=1)
    email: str = Field(..., description="E-mail de quem está devolvendo — pode diferir do usuário logado")
    senha: str = Field(..., min_length=1)


class RequisicaoConfirmacaoResponse(BaseModel):
    id: uuid.UUID
    requisicao_id: uuid.UUID
    tipo: str
    usuario_id: uuid.UUID
    metodo: str
    email_informado: Optional[str] = None
    confirmado_em: datetime

    model_config = {"from_attributes": True}


class ItemRequisicaoResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: Optional[str] = None
    unidade_medida: Optional[str] = None
    deposito_id: Optional[uuid.UUID]
    lote_id: Optional[uuid.UUID]
    quantidade_solicitada: float
    quantidade_aprovada: Optional[float]
    quantidade_entregue: Optional[float]
    quantidade_devolvida: Optional[float] = None
    observacoes: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class RequisicaoResponse(BaseModel):
    id: uuid.UUID
    numero: Optional[str] = None
    unidade_produtiva_id: uuid.UUID
    solicitante_id: uuid.UUID
    solicitante_nome: Optional[str] = None
    aprovador_id: Optional[uuid.UUID]
    aprovador_nome: Optional[str] = None
    data_solicitacao: datetime
    data_necessidade: Optional[date]
    status: str
    origem_tipo: str
    origem_id: Optional[uuid.UUID]
    observacoes: Optional[str]
    itens: List[ItemRequisicaoResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ── Reservas de Estoque ────────────────────────────────────────────────────────

class ReservaCreate(BaseModel):
    produto_id: uuid.UUID
    deposito_id: uuid.UUID
    quantidade: float = Field(..., gt=0)
    motivo: str = Field(..., min_length=3, max_length=255)
    referencia_tipo: Optional[str] = Field(None, max_length=50, description="ORDEM_SERVICO | PEDIDO_COMPRA | SAFRA | REQUISICAO | MANUAL")
    referencia_id: Optional[uuid.UUID] = None


class ReservaCancelarRequest(BaseModel):
    motivo: Optional[str] = Field(None, max_length=255)


class ReservaConsumirRequest(BaseModel):
    quantidade: Optional[float] = Field(None, gt=0, description="Se omitido, consome a quantidade total reservada")
    motivo: Optional[str] = Field(None, max_length=255)


class ReservaResponse(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    deposito_id: uuid.UUID
    criado_por_id: Optional[uuid.UUID]
    quantidade: float
    motivo: str
    referencia_tipo: Optional[str]
    referencia_id: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Alertas ───────────────────────────────────────────────────────────────────

class AlertaEstoqueItem(BaseModel):
    id: uuid.UUID
    produto_id: uuid.UUID
    deposito_id: uuid.UUID
    produto_nome: str
    deposito_nome: str
    quantidade_atual: float
    estoque_minimo: float
    unidade_medida: str
    quantidade_sugerida: float
# ── Auditoria ──────────────────────────────────────────────────────────────────

class LancamentoFinanceiroSimplificado(BaseModel):
    id: uuid.UUID
    valor: float
    categoria: str
    data: date
    model_config = ConfigDict(from_attributes=True)


class AjusteAuditoriaItem(BaseModel):
    id: uuid.UUID
    tipo: str
    quantidade: float
    motivo: Optional[str]
    created_at: datetime
    lancamento_financeiro: Optional[LancamentoFinanceiroSimplificado] = None
    model_config = ConfigDict(from_attributes=True)


class AuditoriaMovimentacaoResponse(BaseModel):
    movimentacao_original: MovimentacaoResponse
    ajustes: List[AjusteAuditoriaItem]
