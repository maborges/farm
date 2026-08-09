"""Cliente compartilhado para chamadas à API da Anthropic (Claude).

Centraliza resolução de API key/modelo, headers e retry/backoff para
todos os serviços do módulo IA que chamam https://api.anthropic.com/v1/messages.
"""
import asyncio
import os

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def get_ia_model() -> str:
    return os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")


async def chamar_anthropic(
    prompt: str,
    *,
    max_tokens: int = 512,
    timeout: float = 15.0,
    max_retries: int = 2,
    backoff_base: float = 1.0,
) -> str:
    """Chama a API de mensagens da Anthropic e retorna o texto da resposta.

    Faz retry com backoff exponencial em erros transitórios (429/5xx) e timeouts.
    Levanta ValueError se ANTHROPIC_API_KEY não estiver configurada.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    payload = {
        "model": get_ia_model(),
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    last_exc: Exception | None = None
    for tentativa in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=payload)
            if resp.status_code in _RETRYABLE_STATUS and tentativa < max_retries:
                await asyncio.sleep(backoff_base * (2 ** tentativa))
                continue
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            if tentativa < max_retries:
                await asyncio.sleep(backoff_base * (2 ** tentativa))
                continue
            raise

    raise last_exc or RuntimeError("Falha ao chamar Anthropic API")
