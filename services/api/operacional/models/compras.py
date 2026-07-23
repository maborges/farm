import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, JSON, Float, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUID
from core.database import Base

class Fornecedor(Base):
    __tablename__ = "compras_fornecedores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)

    # Fornecedor é um "papel de compras" sobre Pessoa — nome, documento,
    # e-mail e telefone são sempre lidos de Pessoa/PessoaDocumento/PessoaContato,
    # nunca duplicados aqui (ver operacional/services/fornecedores_service.py).
    pessoa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    condicoes_pagamento: Mapped[str | None] = mapped_column(String(100))
    prazo_entrega_dias: Mapped[int | None] = mapped_column(Integer)
    avaliacao: Mapped[float | None] = mapped_column(Float)

class PedidoCompra(Base):
    """Pedido de compra oficial gerado a partir de uma cotação ou manual."""
    __tablename__ = "compras_pedidos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    
    # Link com o fluxo de solicitação
    solicitacao_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_solicitacoes.id", ondelete="SET NULL"), nullable=True, index=True)
    cotacao_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_cotacoes.id", ondelete="SET NULL"), nullable=True, index=True)

    # Código de referência legível (ex: PED-2026-000123) — cumpre o papel do
    # id/UUID como identificador único do registro, mas para uso humano
    # (telefone/e-mail com fornecedor). Ver core/sequenciais_config.py.
    numero: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    # Dados do Fornecedor
    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compras_fornecedores.id"), nullable=True, index=True
    )
    fornecedor_nome: Mapped[str] = mapped_column(String(150), nullable=False)
    fornecedor_contato: Mapped[str | None] = mapped_column(String(150))
    condicoes_pagamento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    valor_adiantamento: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0, server_default="0")

    # valor_total é o rollup (soma dos itens em ItemPedidoCompra).
    valor_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ABERTO, ENVIADO, RECEBIDO, CANCELADO
    status: Mapped[str] = mapped_column(String(30), default="ABERTO", index=True)

    # Dashboard de Economia (Step 163)
    economia_absoluta: Mapped[float | None] = mapped_column(Float, default=0.0)
    economia_percentual: Mapped[float | None] = mapped_column(Float, default=0.0)

    # Comprador responsável — herdado da solicitação de origem, usado pelo
    # dashboard de economia por usuário (Step 166, ver obter_economia_por_usuario).
    usuario_solicitante_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="uq_compras_pedidos_tenant_numero"),
    )

    itens: Mapped[list["ItemPedidoCompra"]] = relationship(back_populates="pedido", lazy="noload")


class ItemPedidoCompra(Base):
    """Linha de item de um pedido de compra (um pedido pode ter vários itens).

    `quantidade_solicitada`/`preco_estimado_unitario` são o pedido; `quantidade_recebida`/
    `preco_real_unitario` são acumulados conforme recebimentos parciais chegam
    (ver ItemRecebimento/compras_recebimentos_itens) e usados para status_item.
    """
    __tablename__ = "compras_itens_pedido"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_pedidos.id", ondelete="CASCADE"))
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id"))
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id"), nullable=True)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False, default="UN")

    quantidade_solicitada: Mapped[float] = mapped_column(Float, nullable=False)
    preco_estimado_unitario: Mapped[float] = mapped_column(Float, default=0.0)
    valor_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quantidade_recebida: Mapped[float] = mapped_column(Float, default=0.0)
    preco_real_unitario: Mapped[float | None] = mapped_column(Float, nullable=True)
    # PENDENTE, PARCIAL, COMPLETO, CANCELADO
    status_item: Mapped[str] = mapped_column(String(20), default="PENDENTE")

    pedido: Mapped["PedidoCompra"] = relationship(back_populates="itens")

class RecebimentoParcial(Base):
    """Registro de um recebimento (total ou parcial) de um pedido de compra."""
    __tablename__ = "compras_recebimentos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_pedidos.id", ondelete="CASCADE"), index=True)
    data_recebimento: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    numero_nf: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chave_nfe: Mapped[str | None] = mapped_column(String(60), nullable=True)
    recebido_por_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ItemRecebimento(Base):
    __tablename__ = "compras_recebimentos_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recebimento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_recebimentos.id", ondelete="CASCADE"))
    item_pedido_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_itens_pedido.id"))
    quantidade_recebida: Mapped[float] = mapped_column(Float, nullable=False)
    preco_real_unitario: Mapped[float] = mapped_column(Float, default=0.0)
    numero_lote_fornecedor: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Supplier batch number
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_lotes.id"), nullable=True)


class DevolucaoFornecedor(Base):
    """Devolução de mercadoria ao fornecedor."""
    __tablename__ = "compras_devolucoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_pedidos.id"), nullable=True)
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_fornecedores.id"))
    data_devolucao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # DEFEITO, QUANTIDADE_ERRADA, FORA_SPEC, VENCIDO, OUTRO
    motivo: Mapped[str] = mapped_column(String(30), nullable=False)
    # ABERTA, ENVIADA, CONCLUIDA, RECUSADA
    status: Mapped[str] = mapped_column(String(20), default="ABERTA")
    numero_nf_devolucao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ItemDevolucao(Base):
    __tablename__ = "compras_devolucoes_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    devolucao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_devolucoes.id", ondelete="CASCADE"))
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id"))
    deposito_origem_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id"))
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_lotes.id"), nullable=True)
    quantidade: Mapped[float] = mapped_column(Float, nullable=False)
    custo_unitario: Mapped[float] = mapped_column(Float, default=0.0)


class CotacaoFornecedor(Base):
    """Resposta de um fornecedor a um pedido de compra."""
    __tablename__ = "compras_pedidos_cotacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_pedidos.id", ondelete="CASCADE"))
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_fornecedores.id"))
    
    valor_total: Mapped[float] = mapped_column(Float, nullable=False)
    prazo_entrega_dias: Mapped[int | None] = mapped_column(Integer)
    condicoes_pagamento: Mapped[str | None] = mapped_column(String(200))
    vencimento_cotacao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    selecionada: Mapped[bool] = mapped_column(Boolean, default=False)


class CotacaoCompra(Base):
    """Cotação de preços para uma solicitação de compra."""
    __tablename__ = "compras_cotacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    solicitacao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_solicitacoes.id", ondelete="CASCADE"), index=True)

    # Código de referência legível (ex: COT-2026-000123). Ver core/sequenciais_config.py.
    numero: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compras_fornecedores.id"), nullable=True, index=True
    )
    fornecedor_nome: Mapped[str] = mapped_column(String(150), nullable=False)
    fornecedor_contato: Mapped[str | None] = mapped_column(String(150))
    condicoes_pagamento: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # DEPRECATED: uma cotação agora pode ter múltiplos itens, ver CotacaoItem
    # (compras_cotacoes_itens). valor_total passa a ser o rollup (soma dos itens).
    valor_unitario: Mapped[float | None] = mapped_column(Float, nullable=True)
    valor_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    prazo_entrega_dias: Mapped[int | None] = mapped_column(Integer)

    # RECEBIDA, APROVADA, RECUSADA
    status: Mapped[str] = mapped_column(String(20), default="RECEBIDA", index=True)

    # Alertas de Inteligência
    acima_media: Mapped[bool] = mapped_column(Boolean, default=False)
    percentual_acima_media: Mapped[float | None] = mapped_column(Float, nullable=True)
    mensagem_alerta: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    itens: Mapped[list["CotacaoItem"]] = relationship(back_populates="cotacao", lazy="noload")

    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="uq_compras_cotacoes_tenant_numero"),
    )


class CotacaoItem(Base):
    """Linha de item de uma cotação de fornecedor (uma cotação pode cobrir vários itens)."""
    __tablename__ = "compras_cotacoes_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cotacao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_cotacoes.id", ondelete="CASCADE"), index=True)
    solicitacao_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_solicitacoes_itens.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id"), index=True)

    quantidade: Mapped[float] = mapped_column(Float, nullable=False)
    valor_unitario: Mapped[float] = mapped_column(Float, nullable=False)
    valor_total: Mapped[float] = mapped_column(Float, nullable=False)

    cotacao: Mapped["CotacaoCompra"] = relationship(back_populates="itens")


class AlocacaoItem(Base):
    """Quanto de um item da solicitação foi alocado para comprar de qual
    cotação/fornecedor. Um item pode ter várias alocações (fornecedores
    diferentes, quantidades parciais). `pedido_id` é preenchido quando a
    alocação é convertida em pedido (ver ComprasService.gerar_pedidos_de_alocacoes)."""
    __tablename__ = "compras_alocacoes_item"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    solicitacao_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_solicitacoes_itens.id", ondelete="CASCADE"), index=True)
    cotacao_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_cotacoes_itens.id", ondelete="CASCADE"), index=True)
    quantidade_alocada: Mapped[float] = mapped_column(Float, nullable=False)
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_pedidos.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SolicitacaoCompra(Base):
    """Solicitação interna de compra (etapa prévia ao pedido)."""
    __tablename__ = "compras_solicitacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)

    # Código de referência legível (ex: SOL-2026-000123). Ver core/sequenciais_config.py.
    numero: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    # DEPRECATED: uma solicitação agora pode ter múltiplos itens, ver
    # SolicitacaoItem (compras_solicitacoes_itens).
    produto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id"), index=True, nullable=True)
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id"), index=True, nullable=True)

    quantidade_solicitada: Mapped[float | None] = mapped_column(Float, nullable=True)
    unidade: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # REPOSICAO_ESTOQUE, MANUAL
    origem: Mapped[str] = mapped_column(String(30), default="MANUAL")
    origem_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Quem pediu — só ele pode encerrar a solicitação (ver
    # ComprasService.encerrar_solicitacao). Nullable: registros anteriores a
    # este campo não têm essa informação retroativamente.
    solicitante_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)

    # ABERTA, EM_ANALISE, APROVADA, ENCERRADA, CANCELADA
    status: Mapped[str] = mapped_column(String(20), default="ABERTA", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    itens: Mapped[list["SolicitacaoItem"]] = relationship(back_populates="solicitacao", lazy="noload")

    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="uq_compras_solicitacoes_tenant_numero"),
    )


class SolicitacaoItem(Base):
    """Linha de item de uma solicitação de compra (uma solicitação pode pedir vários produtos)."""
    __tablename__ = "compras_solicitacoes_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    solicitacao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_solicitacoes.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id"), index=True)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id"), index=True)

    quantidade_solicitada: Mapped[float] = mapped_column(Float, nullable=False)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False)

    solicitacao: Mapped["SolicitacaoCompra"] = relationship(back_populates="itens")


class PedidoConfirmacaoFornecedor(Base):
    """Token de confirmação de aceite do pedido enviado ao fornecedor por e-mail.

    Segue o mesmo padrão do ConviteAcesso (core.models.auth): link com token
    exclusivo + senha curta enviada só no corpo do e-mail, para evitar
    confirmação acidental por clique no link.
    """
    __tablename__ = "compras_pedidos_confirmacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compras_pedidos.id", ondelete="CASCADE"), index=True)

    token_confirmacao: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    senha_confirmacao_hash: Mapped[str] = mapped_column(String(255))

    # PENDENTE, CONFIRMADO, RECUSADO, EXPIRADO
    status: Mapped[str] = mapped_column(String(20), default="PENDENTE", index=True)
    tentativas_senha: Mapped[int] = mapped_column(Integer, default=0)

    data_expiracao: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    respondido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
