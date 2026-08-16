import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Text, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from core.database import Base


class DispositivoBalanca(Base):
    """Estação de balança (dispositivo fixo), não vinculada a um operador específico."""
    __tablename__ = "balanca_dispositivos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    device_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activation_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    activation_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="PENDENTE", nullable=False)
    # PENDENTE → aguardando ativação | ATIVO | REVOGADO

    fazenda_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_balanca_disp_tenant_status", "tenant_id", "status"),
        Index("ix_balanca_disp_activation", "activation_code"),
    )


class OrdemPesagem(Base):
    """Solicitação de pesagem criada por um módulo cliente (romaneio, compras, vendas,
    pecuária, pessoas). Não referencia tabelas de outros módulos diretamente — origem
    é identificada de forma genérica para manter o módulo desacoplável."""
    __tablename__ = "balanca_ordens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    origem_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    # COLHEITA | COMPRA | VENDA | PECUARIA | PESSOA | OUTRO
    origem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # VEICULO | ANIMAL | PESSOA
    tipo_pesagem: Mapped[str] = mapped_column(String(10), nullable=False)
    # UNICA | DUPLA

    status: Mapped[str] = mapped_column(String(20), default="PENDENTE", nullable=False, index=True)
    # PENDENTE | EM_PESAGEM | CONCLUIDA | CANCELADA

    solicitado_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    contexto: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # dados livres do módulo cliente (placa, motorista, produto, brinco, lote etc.)

    dispositivo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("balanca_dispositivos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    concluida_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_balanca_ordens_tenant_status", "tenant_id", "status"),
        Index("ix_balanca_ordens_origem", "origem_tipo", "origem_id"),
    )


class Pesagem(Base):
    """Resultado (ticket) de uma pesagem, vinculado a uma OrdemPesagem."""
    __tablename__ = "balanca_pesagens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("balanca_ordens.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dispositivo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("balanca_dispositivos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    numero_ticket: Mapped[str] = mapped_column(String(30), nullable=False)

    # Identificador local do dispositivo (UUID gerado offline), para idempotência no sync
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    peso_bruto_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    peso_tara_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    peso_liquido_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)

    captured_via: Mapped[str] = mapped_column(String(15), default="MANUAL", nullable=False)
    # MANUAL | ELETRONICA
    leitura_bruta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # payload cru vindo da ponte de hardware (protocolo do indicador), quando aplicável

    placa: Mapped[str | None] = mapped_column(String(10), nullable=True)
    motorista: Mapped[str | None] = mapped_column(String(150), nullable=True)
    animal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    pessoa_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    data_entrada: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data_saida: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", name="uq_balanca_pesagem_tenant_client"),
        UniqueConstraint("tenant_id", "numero_ticket", name="uq_balanca_pesagem_tenant_ticket"),
        Index("ix_balanca_pesagens_ordem", "ordem_id"),
    )


class SyncTombstoneBalanca(Base):
    """Registra deleções para que dispositivos de balança offline saibam o que remover no próximo pull."""
    __tablename__ = "balanca_sync_tombstones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_balanca_tombstones_tenant_type_deleted", "tenant_id", "entity_type", "deleted_at"),
    )
