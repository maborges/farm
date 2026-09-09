import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, ForeignKeyConstraint, JSON, Integer, Numeric, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from sqlalchemy import Uuid as UUID
from core.database import Base

class Deposito(Base):
    """Armazéns, galpões ou tanques de combustível."""
    __tablename__ = "estoque_depositos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    unidade_produtiva_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("unidades_produtivas.id"), index=True)
    
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), default="GERAL") # GERAL, COMBUSTIVEL, DEFENSIVOS, PECAS
    localizacao_desc: Mapped[str | None] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_estoque_depositos_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "unidade_produtiva_id"],
            ["unidades_produtivas.tenant_id", "unidades_produtivas.id"],
            name="fk_ed_tenant_unidade_produtiva",
            ondelete="NO ACTION",
        ),
    )

class SaldoEstoque(Base):
    """Ponte entre Produto e Depósito para controle de quantidade atual."""
    __tablename__ = "estoque_saldos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), index=True)
    
    quantidade_atual: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    quantidade_reservada: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    estoque_minimo: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    estoque_maximo: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    # Custo Médio Ponderado Móvel (CMPM/Kardex) — só muda em entradas; saídas,
    # transferências e ajustes negativos consomem a este custo sem alterá-lo.
    # Nunca é zerado quando o saldo esgota (fica "congelado" até a próxima
    # entrada recalcular). Ver EstoqueService.registrar_entrada.
    custo_medio: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    ultima_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class EstoqueLocalizacao(Base):
    """Endereço físico (corredor/prateleira/posição) de um produto dentro de um
    depósito. Um mesmo produto pode ter várias localizações no mesmo depósito
    (quantidade fracionada entre elas)."""
    __tablename__ = "estoque_localizacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), index=True)

    corredor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prateleira: Mapped[str | None] = mapped_column(String(20), nullable=True)
    posicao: Mapped[str | None] = mapped_column(String(20), nullable=True)
    codigo_localizacao: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True, comment="Etiqueta/código do endereço físico, para leitor de código de barras")
    observacao_livre: Mapped[str | None] = mapped_column(String(200), nullable=True)

    quantidade: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_estloc_produto_deposito", produto_id, deposito_id),
    )

class LoteEstoque(Base):
    """Rastreabilidade por lote de produto (defensivos, sementes, ração)."""
    __tablename__ = "estoque_lotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), index=True)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), index=True)

    numero_lote: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    data_fabricacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_validade: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    quantidade_inicial: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    quantidade_atual: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    custo_unitario: Mapped[float] = mapped_column(Numeric(15, 6), default=0.0)
    nota_fiscal_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    qualidade_laudo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("operacional_qualidade_laudos.id", ondelete="SET NULL"), nullable=True, index=True)
    qualidade_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    peso_desconto_qualidade_kg: Mapped[float] = mapped_column(Numeric(12, 3), default=0.0, nullable=False, server_default="0")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ATIVO, VENCIDO, ESGOTADO, BLOQUEADO
    status: Mapped[str] = mapped_column(String(20), default="ATIVO")
    lote_beneficiamento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True, comment="FK rastreabilidade: qual lote beneficiamento originou este estoque")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RequisicaoMaterial(Base):
    """Solicitação interna de material ao almoxarifado."""
    __tablename__ = "estoque_requisicoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)

    # Código de referência legível (ex: REQ-2026-000123). Ver core/sequenciais_config.py.
    numero: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    unidade_produtiva_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("unidades_produtivas.id"), index=True)
    solicitante_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    aprovador_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    operacao_agricola_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"), nullable=True, index=True,
        comment="Vínculo formal com a OS que originou esta requisição (auto-gerada ao confirmar a OS). Pode haver mais de uma requisição por OS (complementos)."
    )
    data_solicitacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    data_necessidade: Mapped[date | None] = mapped_column(Date, nullable=True)
    # PENDENTE, APROVADA, SEPARANDO, ENTREGUE, RECUSADA, CANCELADA
    status: Mapped[str] = mapped_column(String(20), default="PENDENTE")
    # ORDEM_SERVICO, MANUTENCAO, PRODUCAO, OUTRO
    origem_tipo: Mapped[str] = mapped_column(String(30), default="OUTRO")
    origem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    itens: Mapped[list["ItemRequisicao"]] = relationship(back_populates="requisicao", lazy="noload")

    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="uq_estoque_requisicoes_tenant_numero"),
    )


class ItemRequisicao(Base):
    __tablename__ = "estoque_requisicoes_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requisicao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_requisicoes.id", ondelete="CASCADE"))
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id"))
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id"), nullable=True)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_lotes.id"), nullable=True)
    quantidade_solicitada: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    quantidade_aprovada: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    quantidade_entregue: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    quantidade_devolvida: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    requisicao: Mapped["RequisicaoMaterial"] = relationship(back_populates="itens")


class RequisicaoConfirmacao(Base):
    """Assinatura eletrônica (reautenticação) de retirada ou devolução de
    material de uma requisição — REQUISICAO-MATERIAL-01 Fase 2."""
    __tablename__ = "estoque_requisicao_confirmacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    requisicao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_requisicoes.id", ondelete="CASCADE"), index=True)
    # RETIRADA | DEVOLUCAO
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    # SENHA (web, e-mail+senha) | TOKEN_DISPOSITIVO (app de campo)
    metodo: Mapped[str] = mapped_column(String(20), nullable=False)
    email_informado: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ReservaEstoque(Base):
    """Bloqueio de saldo para uso futuro garantido (OS, safra, pedido)."""
    __tablename__ = "estoque_reservas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), index=True)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), index=True)
    criado_por_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)

    quantidade: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    # ORDEM_SERVICO, PEDIDO_COMPRA, SAFRA, REQUISICAO, MANUAL
    referencia_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # ATIVA, CONSUMIDA, CANCELADA
    status: Mapped[str] = mapped_column(String(20), default="ATIVA", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class EstoqueMovimento(Base):
    """Ledger append-only de estoque. Correções são novos movimentos via ajuste_de."""
    __tablename__ = "estoque_movimentos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    data_movimento: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    tipo_movimento: Mapped[str] = mapped_column(String(24), nullable=False)

    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="RESTRICT"), nullable=False, index=True)
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="SET NULL"), nullable=True, index=True)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_lotes.id", ondelete="SET NULL"), nullable=True, index=True)

    quantidade: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    unidade_medida_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("unidades_medida.id", ondelete="RESTRICT"), nullable=False)
    custo_unitario: Mapped[float | None] = mapped_column(Numeric(15, 6), nullable=True)
    custo_total: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    origem: Mapped[str] = mapped_column(String(32), nullable=False)
    origem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    operacao_execucao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operacoes_execucoes.id", ondelete="SET NULL"), nullable=True
    )
    production_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_units.id", ondelete="SET NULL"), nullable=True
    )
    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compras_fornecedores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    numero_lote: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ajuste_de: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estoque_movimentos.id", ondelete="SET NULL"), nullable=True
    )
    # Snapshot do CMPM (SaldoEstoque.custo_medio) antes/depois deste movimento —
    # dá o kardex completo direto pelo ledger, sem recálculo, e permite reverter
    # o custo médio com precisão em estornos (ver ComprasService.estornar_recebimento).
    custo_medio_anterior: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    custo_medio_resultante: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Compatibilidade com o nomeado antigo usado em serviços/routers legados.
    data_movimentacao = synonym("data_movimento")
    tipo = synonym("tipo_movimento")
    origem_tipo = synonym("origem")
    motivo = synonym("observacoes")

    def __init__(self, **kwargs):
        legacy_to_current = {
            "data_movimentacao": "data_movimento",
            "tipo": "tipo_movimento",
            "origem_tipo": "origem",
            "motivo": "observacoes",
        }
        for legacy_key, current_key in legacy_to_current.items():
            if legacy_key in kwargs and current_key not in kwargs:
                kwargs[current_key] = kwargs.pop(legacy_key)

        # Chamadas legadas ainda passam usuario_id, mas o ledger atual não usa esse campo.
        kwargs.pop("usuario_id", None)

        super().__init__(**kwargs)
