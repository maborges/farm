import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Numeric, Index
from sqlalchemy import Uuid as UUIDTYPE
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class IACreditosPacote(Base):
    __tablename__ = "ia_creditos_pacotes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    quantidade_creditos: Mapped[int] = mapped_column(Integer, nullable=False)
    creditos_usados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    origem: Mapped[str] = mapped_column(String(60), nullable=False, default="SOLICITACAO")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="ATIVO")
    adquirido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expira_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_creditos_tenant_status", "tenant_id", "status"),
    )


class IAUso(Base):
    __tablename__ = "ia_uso"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    origem: Mapped[str] = mapped_column(String(60), nullable=False)
    modelo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    tokens_entrada: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_saida: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    custo_estimado: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="SUCESSO")
    fonte_consumo: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # PLANO | PACOTE
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_uso_tenant_created", "tenant_id", "created_at"),
    )
