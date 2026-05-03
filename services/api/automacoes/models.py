import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Boolean, UniqueConstraint, Index
from sqlalchemy import Uuid as UUIDTYPE
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from core.database import Base


class AutomacaoExecucao(Base):
    __tablename__ = "automacoes_execucoes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    safra_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("safras.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    executado_por: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    regras_disparadas: Mapped[list] = mapped_column(JSON, default=list)
    acoes_criadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notificacoes_criadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="SUCESSO")
    mensagem: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AutomacaoConfiguracao(Base):
    __tablename__ = "automacoes_configuracoes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    safra_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("safras.id", ondelete="CASCADE"),
        nullable=True,
    )
    regra: Mapped[str] = mapped_column(String(60), nullable=False)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    frequencia: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default="MANUAL")
    proxima_execucao: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "safra_id", "regra", name="uq_automacao_config_regra"),
        Index("ix_automacoes_conf_tenant", "tenant_id"),
    )
