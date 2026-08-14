from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON, ForeignKey, DateTime, Index, UniqueConstraint, text
from sqlalchemy import Uuid as UUIDTYPE
from uuid import UUID
import uuid
from datetime import datetime
from typing import Optional

from core.database import Base


class Notificacao(Base):
    __tablename__ = "notificacoes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensagem: Mapped[str] = mapped_column(String(1000), nullable=False)
    nivel: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")
    lida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    origem: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    origem_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    usuario_id: Mapped[Optional[UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("(CURRENT_TIMESTAMP)"), nullable=False
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificacaoLeitura(Base):
    """Estado de leitura por usuário. Ausência de linha = não lida."""
    __tablename__ = "notificacoes_leituras"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notificacao_id: Mapped[UUID] = mapped_column(
        ForeignKey("notificacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lida: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("(CURRENT_TIMESTAMP)"), nullable=False
    )
    acao: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="Ação disparada a partir da notificação, ex: accept, dismiss, pagar")
    acao_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("notificacao_id", "usuario_id", name="uq_notificacao_leitura_usuario"),
        Index("ix_notificacoes_leituras_tenant_usuario", tenant_id, usuario_id),
    )


class NotificacaoPreferencia(Base):
    __tablename__ = "notificacoes_preferencias"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    email_ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sistema_ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    whatsapp_ativo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Horário de envio (ex: "07:00") - Relevante para tipo=RESUMO_DIARIO
    horario_envio: Mapped[str] = mapped_column(String(5), default="07:00", nullable=False)
    
    # Nível de sensibilidade: ALTO (todos), MEDIO (avisos+criticos), BAIXO (apenas criticos)
    nivel_sensibilidade: Mapped[str] = mapped_column(String(20), default="ALTO", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        server_default=text("(CURRENT_TIMESTAMP)"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("(CURRENT_TIMESTAMP)"), 
        nullable=False, 
        onupdate=text("(CURRENT_TIMESTAMP)")
    )
