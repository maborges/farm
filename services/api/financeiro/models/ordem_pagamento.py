"""Entidades de ordem de pagamento para remessas bancárias."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class OrdemPagamento(Base):
    """Lote de pagamentos de uma conta bancária em determinada data."""

    __tablename__ = "fin_ordens_pagamento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    conta_bancaria_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fin_contas_bancarias.id", ondelete="RESTRICT"), nullable=False)
    data_pagamento: Mapped[date] = mapped_column(Date, nullable=False)
    banco_codigo: Mapped[str] = mapped_column(String(3), nullable=False)
    ambiente: Mapped[str] = mapped_column(String(20), nullable=False, default="HOMOLOGACAO")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RASCUNHO")
    sequencial: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_valor: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    arquivo_nome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    arquivo_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ItemOrdemPagamento(Base):
    """Título individual incluído em uma ordem de pagamento."""

    __tablename__ = "fin_itens_ordem_pagamento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    ordem_pagamento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fin_ordens_pagamento.id", ondelete="CASCADE"), nullable=False, index=True)
    despesa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fin_despesas.id", ondelete="RESTRICT"), nullable=False, index=True)
    valor: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    forma_pagamento: Mapped[str] = mapped_column(String(20), nullable=False)
    favorecido_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    dados_pagamento_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDENTE")
    motivo_rejeicao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
