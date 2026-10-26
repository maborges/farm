"""Utilitário de higienização e mascaramento de configurações sensíveis.

Garante que senhas, tokens, chaves de API e segredos criptográficos
nunca sejam serializados em texto claro nas respostas de API do Backoffice
ou registrados em logs de auditoria.
"""

from __future__ import annotations

import copy
import re
from typing import Any

SENSITIVE_FIELD_PATTERNS = [
    re.compile(r"pass(word)?", re.IGNORECASE),
    re.compile(r"pwd", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"credentials?", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"cipher(text)?", re.IGNORECASE),
]

SENSITIVE_KEY_NAMESPACES = {
    "smtp_global",
    "stripe_keys",
    "asaas_keys",
    "agro:clima:credentials",
    "platform:secrets",
}


def is_sensitive_key(key_name: str) -> bool:
    """Verifica se um nome de chave ou namespace é considerado sensível."""
    if key_name.lower() in SENSITIVE_KEY_NAMESPACES:
        return True
    return any(pattern.search(key_name) for pattern in SENSITIVE_FIELD_PATTERNS)


def mask_string_value(value: str) -> str:
    """Mascara uma string preservando prefixo e sufixo quando longa o suficiente."""
    if not value:
        return ""
    length = len(value)
    if length <= 8:
        return "********"
    # Preserva primeiros 4 caracteres e últimos 4 caracteres
    prefix = value[:4]
    suffix = value[-4:]
    return f"{prefix}***...{suffix}"


def mask_sensitive_data(data: Any, parent_key: str = "") -> Any:
    """Mascara recursivamente dados sensíveis em dicionários, listas ou strings soltas."""
    if data is None:
        return None

    if isinstance(data, dict):
        masked_dict: dict[str, Any] = {}
        for k, v in data.items():
            if is_sensitive_key(str(k)):
                if isinstance(v, str):
                    masked_dict[k] = mask_string_value(v)
                elif isinstance(v, (dict, list)):
                    masked_dict[k] = mask_sensitive_data(v, parent_key=str(k))
                else:
                    masked_dict[k] = "********"
            else:
                masked_dict[k] = mask_sensitive_data(v, parent_key=str(k))
        return masked_dict

    if isinstance(data, list):
        return [mask_sensitive_data(item, parent_key=parent_key) for item in data]

    if isinstance(data, str) and is_sensitive_key(parent_key):
        return mask_string_value(data)

    return data
