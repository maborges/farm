import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
import sqlalchemy as sa
from core.database import Base


class DispositivoCampo(Base):
    __tablename__ = "campo_dispositivos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    device_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    activation_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    activation_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="PENDENTE", nullable=False)
    # PENDENTE → aguardando ativação | ATIVO | REVOGADO

    fazenda_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    modulos: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_campo_disp_tenant_user", "tenant_id", "user_id"),
        Index("ix_campo_disp_status", "status"),
        Index("ix_campo_disp_activation", "activation_code"),
    )


class TarefaCampo(Base):
    """Tarefas criadas offline no dispositivo de campo e sincronizadas via /sync/push."""
    __tablename__ = "campo_tarefas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dispositivo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campo_dispositivos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # Identificador local do cliente (UUID gerado no dispositivo)
    client_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(20), nullable=False)
    # agricola | pecuaria

    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    area_rural_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="PENDENTE", nullable=False, index=True)

    dados: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fotos: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)

    localizacao_status: Mapped[str] = mapped_column(String(20), default="INDISPONIVEL", nullable=False)
    latitude: Mapped[float | None] = mapped_column(sa.Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(sa.Numeric(10, 7), nullable=True)

    # Timestamps do cliente (para conflict resolution)
    client_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    client_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", name="uq_campo_tarefa_tenant_client"),
        Index("ix_campo_tarefas_tenant_status", "tenant_id", "status"),
        Index("ix_campo_tarefas_unidade", "unidade_produtiva_id"),
        Index("ix_campo_tarefas_type", "type"),
    )


class SyncTombstone(Base):
    """Registra deleções para que dispositivos offline saibam o que remover no próximo pull."""
    __tablename__ = "campo_sync_tombstones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_tombstones_tenant_type_deleted", "tenant_id", "entity_type", "deleted_at"),
    )
