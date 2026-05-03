import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, DateTime, Index
from sqlalchemy import Uuid as SAUUID
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class SolicitacaoHistorico(Base):
    __tablename__ = "billing_solicitacoes_comerciais_historico"

    id: Mapped[uuid.UUID] = mapped_column(SAUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    solicitacao_id: Mapped[uuid.UUID] = mapped_column(SAUUID(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(SAUUID(as_uuid=True), nullable=False)
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(SAUUID(as_uuid=True), nullable=True)
    tipo_evento: Mapped[str] = mapped_column(String(50), nullable=False)
    valor_anterior: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    valor_novo: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_sol_hist_solicitacao_created", "solicitacao_id", "created_at"),
    )
