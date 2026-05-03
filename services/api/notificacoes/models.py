from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON, ForeignKey, DateTime, text
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
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("(CURRENT_TIMESTAMP)"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("(CURRENT_TIMESTAMP)"), 
        nullable=False, 
        onupdate=text("(CURRENT_TIMESTAMP)")
    )
