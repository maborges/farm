"""Utilitários de segurança para credenciais de integrações."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from core.config import settings

_PREFIX = "enc::"


def _build_fernet() -> Fernet:
    raw_secret = settings.integrations_secret_key or settings.jwt_secret_key
    digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_integration_secret(value: str) -> str:
    """Criptografa um segredo de integração para persistência."""
    if not value:
        return ""
    token = _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_integration_secret(value: str | None) -> str:
    """
    Descriptografa um segredo de integração.

    Mantém compatibilidade com dados legados em texto puro enquanto a rotação
    completa das credenciais não é executada.
    """
    if not value:
        return ""
    if not value.startswith(_PREFIX):
        return value
    token = value[len(_PREFIX) :]
    try:
        return _build_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def is_integration_secret_encrypted(value: str | None) -> bool:
    return bool(value and value.startswith(_PREFIX))


def mask_integration_secret(value: str | None) -> str | None:
    if not value:
        return None
    return "••••••••"
