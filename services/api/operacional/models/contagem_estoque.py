import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from core.database import Base


class ContagemEstoque(Base):
    """Sessão de contagem física (cycle count) de um depósito.

    OPERATIONS-GAP-01 §21.30 — agrupa N `ContagemEstoqueItem` sob um único
    cabeçalho, permitindo registrar a quantidade contada de cada produto
    separadamente da aplicação no saldo (revisão antes de aplicar), e ao
    concluir gera ajustes em `EstoqueMovimento` via
    `EstoqueService.registrar_ajuste` para os itens divergentes.
    """
    __tablename__ = "estoque_contagens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deposito_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(20), default="ABERTA", nullable=False)
    aberta_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    aberta_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    concluida_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_estoque_contagens_tenant_deposito_status", "tenant_id", "deposito_id", "status"),
    )


class ContagemEstoqueItem(Base):
    """Item de uma sessão de contagem — 1 por produto com saldo no depósito no momento da abertura."""
    __tablename__ = "estoque_contagem_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contagem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estoque_contagens.id", ondelete="CASCADE"), nullable=False, index=True
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), nullable=False, index=True
    )

    quantidade_sistema: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    quantidade_contada: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    contado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    movimento_ajuste_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estoque_movimentos.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_estoque_contagem_itens_tenant_contagem", "tenant_id", "contagem_id"),
    )
