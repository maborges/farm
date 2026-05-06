import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Numeric, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from core.database import Base


class FinanceiroSafraCenario(Base):
    __tablename__ = "financeiro_safra_cenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    safra_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    receita_percentual: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    custos_percentual: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    resultado_simulado: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    margem_simulada: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    escolhido: Mapped[bool] = mapped_column(default=False)
    escolhido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recomendado_pela_ia: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
