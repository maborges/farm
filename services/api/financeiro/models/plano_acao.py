import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from core.database import Base


class PlanoAcaoItem(Base):
    __tablename__ = "financeiro_plano_acoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    safra_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    prioridade: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIA")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDENTE")
    rota: Mapped[str] = mapped_column(String(200), nullable=False)
    origem: Mapped[str] = mapped_column(String(30), nullable=False, default="AUTO")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    concluido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ignorado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_plano_acoes_tenant_safra", "tenant_id", "safra_id"),
        Index("ix_plano_acoes_tipo_safra", "safra_id", "tipo"),
    )
