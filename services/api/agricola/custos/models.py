import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUIDType

from core.database import Base


class CostAllocation(Base):
    """Agricultural cost allocation by ProductionUnit."""

    __tablename__ = "cost_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    production_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), ForeignKey("production_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType(as_uuid=True), nullable=True)
    operation_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True), ForeignKey("operacoes_execucoes.id", ondelete="SET NULL"), nullable=True
    )
    inventory_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True), ForeignKey("estoque_movimentos.id", ondelete="SET NULL"), nullable=True
    )
    fin_rateio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True), ForeignKey("fin_rateios.id", ondelete="SET NULL"), nullable=True
    )
    cost_category: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    allocation_date: Mapped[date] = mapped_column(Date, nullable=False)
    allocation_method: Mapped[str] = mapped_column(String(24), nullable=False, default="DIRECT")
    allocation_basis: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ProdutoColhidoCostAllocation(Base):
    """Alternativa C (OPERATIONS-GAP-01): rateio persistido entre ProdutoColhido (lote)
    e CostAllocation (custo do PU), com override manual auditável."""

    __tablename__ = "agricola_produto_colhido_cost_allocations"
    __table_args__ = (
        UniqueConstraint("produto_colhido_id", "cost_allocation_id", name="uq_produto_colhido_cost_allocation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    produto_colhido_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), ForeignKey("agricola_produtos_colhidos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cost_allocation_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), ForeignKey("cost_allocations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valor_atribuido: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    percentual_atribuido: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    origem_calculo: Mapped[str] = mapped_column(String(20), nullable=False, default="AUTOMATICO")
    justificativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )
