from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class MaturidadeSnapshot(Base):
    """Snapshot mensal do score consolidado de maturidade da fazenda (4 pilares)."""

    __tablename__ = "maturidade_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "unidade_produtiva_id", "competencia", name="uq_maturidade_competencia"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unidades_produtivas.id", ondelete="CASCADE"), nullable=True, index=True
    )
    competencia: Mapped[str] = mapped_column(String(7), nullable=False, index=True)

    score_geral: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pilar_operacional: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pilar_agronomico_zootecnico: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pilar_economico: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pilar_financeiro: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    detalhes: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
