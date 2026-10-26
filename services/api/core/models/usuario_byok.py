"""Modelo ORM para o cofre de credenciais BYOK vinculado à identidade global (PostgreSQL).

Implementa:
1. Vínculo canônico com a tabela `usuarios.id` (sem necessidade de tenant comercial).
2. Envelope Encryption (AES-256-GCM + DEK 256 bits + KEK versionada).
3. Isolamento criptográfico estrito por usuário.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class UsuarioByokCredential(Base):
    """Cofre individual de credenciais de cotações BYOK (Bring Your Own Key)."""

    __tablename__ = "usuario_byok_credenciais"
    __table_args__ = (
        UniqueConstraint("usuario_id", "provider_slug", name="uq_usuario_byok_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    mascara_chave: Mapped[str] = mapped_column(String(50), nullable=False)
    ciphertext_b64: Mapped[str] = mapped_column(String(1024), nullable=False)
    data_nonce_b64: Mapped[str] = mapped_column(String(64), nullable=False)
    dek_encrypted_b64: Mapped[str] = mapped_column(String(256), nullable=False)
    dek_nonce_b64: Mapped[str] = mapped_column(String(64), nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="CONECTADO", nullable=False)
    ultimo_uso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
