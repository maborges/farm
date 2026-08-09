"""Mascaramento de campos sensíveis em payloads de integração (tokens, senhas, certificados)."""
from __future__ import annotations

from typing import Any

_SENSITIVE_TOKENS = (
    "password",
    "token",
    "secret",
    "private_key",
    "certificate",
    "api_key",
    "authorization",
)


def mask_sensitive_payload(payload: Any) -> Any:
    """Substitui valores de chaves sensíveis (senha, token, api_key etc.) por máscara, recursivamente."""
    if isinstance(payload, dict):
        masked: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = key.lower()
            if any(token in lowered for token in _SENSITIVE_TOKENS):
                masked[key] = "••••••••"
            else:
                masked[key] = mask_sensitive_payload(value)
        return masked
    if isinstance(payload, list):
        return [mask_sensitive_payload(item) for item in payload]
    return payload
