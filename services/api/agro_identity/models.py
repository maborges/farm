"""Modelos ORM para identidades individuais e cofre BYOK do DeepFarms Agro."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import AgroBase


class AgroUsuario(AgroBase):
    """Conta de usuário individual do DeepFarms Agro (gratuita, sem vínculo com tenant comercial)."""

    __tablename__ = "agro_usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    sessoes: Mapped[list["AgroSessao"]] = relationship(
        "AgroSessao", back_populates="usuario", cascade="all, delete-orphan", lazy="selectin"
    )
    tokens_recuperacao: Mapped[list["AgroTokenRecuperacao"]] = relationship(
        "AgroTokenRecuperacao", back_populates="usuario", cascade="all, delete-orphan", lazy="selectin"
    )
    tokens_verificacao: Mapped[list["AgroTokenVerificacao"]] = relationship(
        "AgroTokenVerificacao", back_populates="usuario", cascade="all, delete-orphan", lazy="selectin"
    )
    credenciais_byok: Mapped[list["AgroUserByokCredential"]] = relationship(
        "AgroUserByokCredential", back_populates="usuario", cascade="all, delete-orphan", lazy="selectin"
    )


class AgroSessao(AgroBase):
    """Sessão revogável com expiração e identificação única por token_hash."""

    __tablename__ = "agro_sessoes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agro_usuarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revogado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    ultimo_acesso: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    usuario: Mapped[AgroUsuario] = relationship("AgroUsuario", back_populates="sessoes")


class AgroTokenRecuperacao(AgroBase):
    """Token de recuperação de senha emitido para redefinição segura de acesso."""

    __tablename__ = "agro_tokens_recuperacao"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agro_usuarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    usuario: Mapped[AgroUsuario] = relationship("AgroUsuario", back_populates="tokens_recuperacao")


class AgroTokenVerificacao(AgroBase):
    """Código numérico de confirmação e verificação de e-mail."""

    __tablename__ = "agro_tokens_verificacao"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agro_usuarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    codigo: Mapped[str] = mapped_column(String(6), index=True, nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    usuario: Mapped[AgroUsuario] = relationship("AgroUsuario", back_populates="tokens_verificacao")


class AgroUserByokCredential(AgroBase):
    """Estrutura persistente do cofre segregado BYOK (Envelope Encryption com DEK e KEK)."""

    __tablename__ = "agro_user_byok_credentials"
    __table_args__ = (
        UniqueConstraint("usuario_id", "provider_slug", name="uq_agro_byok_user_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agro_usuarios.id", ondelete="CASCADE"), index=True, nullable=False
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

    usuario: Mapped[AgroUsuario] = relationship("AgroUsuario", back_populates="credenciais_byok")
