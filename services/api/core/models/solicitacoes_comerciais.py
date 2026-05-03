import uuid
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal
from sqlalchemy import ForeignKey, String, Numeric, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class SolicitacaoComercial(Base):
    __tablename__ = "billing_solicitacoes_comerciais"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # CREDITOS_IA | UPGRADE_PLANO
    origem: Mapped[str] = mapped_column(String(100), nullable=False)  # ia_creditos_adicionais
    detalhes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ABERTA", server_default="ABERTA")
    valor_estimado: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    link_pagamento: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status_pagamento: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, server_default="PENDENTE")
    observacao_comercial: Mapped[Optional[str]] = mapped_column(nullable=True)
    responsavel_usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    proximo_followup_em: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    followup_observacao: Mapped[Optional[str]] = mapped_column(nullable=True)
    crm_sync_status: Mapped[str] = mapped_column(
        String(20), default="NAO_ENVIADO", server_default="NAO_ENVIADO", nullable=False
    )
    crm_sync_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_solicitacoes_tenant_tipo", "tenant_id", "tipo"),
        Index("ix_solicitacoes_status", "status"),
    )
