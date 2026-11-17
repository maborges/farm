"""Cliente compartilhado multi-provider da DeepFarmIA (Anthropic, Gemini, Groq e Ollama).

Centraliza resolução de provider/API key/modelo, headers e retry/backoff para
todos os serviços do módulo IA, mantendo `chamar_anthropic` e `get_ia_model`
compatíveis com os callers existentes.
"""
import asyncio
import os

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def get_ia_provider() -> str:
    """Resolve o provedor ativo via `IA_PROVIDER` ou auto-detecção pelas chaves no ambiente."""
    explicit = os.getenv("IA_PROVIDER", "auto").strip().lower()
    if explicit and explicit != "auto":
        return explicit
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return "anthropic"
    if os.getenv("GEMINI_API_KEY", "").strip():
        return "gemini"
    if os.getenv("GROQ_API_KEY", "").strip():
        return "groq"
    if os.getenv("OLLAMA_BASE_URL", "").strip():
        return "ollama"
    return "anthropic"


def has_ia_configured() -> bool:
    """Retorna True se o provedor ativo possui chave/URL configurada."""
    provider = get_ia_provider()
    if provider == "gemini":
        return bool(os.getenv("GEMINI_API_KEY", "").strip())
    if provider == "groq":
        return bool(os.getenv("GROQ_API_KEY", "").strip())
    if provider == "ollama":
        return bool(os.getenv("OLLAMA_BASE_URL", "").strip())
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def get_ia_model() -> str:
    """Retorna o modelo configurado para o provedor ativo."""
    provider = get_ia_provider()
    custom = os.getenv("IA_MODEL", "").strip()
    if custom and not (provider != "anthropic" and custom.startswith("claude-")):
        return custom
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    if provider == "groq":
        return os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    return "claude-haiku-4-5-20251001"


async def _post_with_retry(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict,
    timeout: float,
    max_retries: int,
    backoff_base: float,
) -> dict:
    last_exc: Exception | None = None
    for tentativa in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code in _RETRYABLE_STATUS and tentativa < max_retries:
                await asyncio.sleep(backoff_base * (2 ** tentativa))
                continue
            resp.raise_for_status()
            return resp.json()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            if tentativa < max_retries:
                await asyncio.sleep(backoff_base * (2 ** tentativa))
                continue
            raise
    raise last_exc or RuntimeError("Falha ao chamar provedor de IA")


async def _chamar_gemini(
    prompt: str,
    *,
    max_tokens: int,
    timeout: float,
    max_retries: int,
    backoff_base: float,
) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada")
    model = _get_model_for_provider("gemini")
    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={api_key}"
    data = await _post_with_retry(
        url,
        headers={"content-type": "application/json"},
        payload={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        },
        timeout=timeout,
        max_retries=max_retries,
        backoff_base=backoff_base,
    )
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _chamar_groq(
    prompt: str,
    *,
    max_tokens: int,
    timeout: float,
    max_retries: int,
    backoff_base: float,
) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY não configurada")
    data = await _post_with_retry(
        GROQ_CHAT_URL,
        headers={
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        payload={
            "model": _get_model_for_provider("groq"),
            "max_tokens": max(max_tokens, 1500),
            "reasoning_effort": "low",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
        max_retries=max_retries,
        backoff_base=backoff_base,
    )
    return (data["choices"][0]["message"].get("content") or "").strip()


async def _chamar_ollama(
    prompt: str,
    *,
    max_tokens: int,
    timeout: float,
    max_retries: int,
    backoff_base: float,
) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise ValueError("OLLAMA_BASE_URL não configurada")
    data = await _post_with_retry(
        f"{base_url}/api/generate",
        headers={"content-type": "application/json"},
        payload={
            "model": _get_model_for_provider("ollama"),
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        },
        timeout=timeout,
        max_retries=max_retries,
        backoff_base=backoff_base,
    )
    return data["response"].strip()


async def _chamar_provider(
    provider: str,
    prompt: str,
    *,
    max_tokens: int,
    timeout: float,
    max_retries: int,
    backoff_base: float,
) -> str:
    if provider == "gemini":
        return await _chamar_gemini(
            prompt, max_tokens=max_tokens, timeout=timeout, max_retries=max_retries, backoff_base=backoff_base
        )
    if provider == "groq":
        return await _chamar_groq(
            prompt, max_tokens=max_tokens, timeout=timeout, max_retries=max_retries, backoff_base=backoff_base
        )
    if provider == "ollama":
        return await _chamar_ollama(
            prompt, max_tokens=max_tokens, timeout=timeout, max_retries=max_retries, backoff_base=backoff_base
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    data = await _post_with_retry(
        ANTHROPIC_MESSAGES_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        payload={
            "model": _get_model_for_provider("anthropic"),
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
        max_retries=max_retries,
        backoff_base=backoff_base,
    )
    return data["content"][0]["text"].strip()


def _get_model_for_provider(provider: str) -> str:
    custom = os.getenv("IA_MODEL", "").strip()
    if custom and not (provider != "anthropic" and custom.startswith("claude-")):
        return custom
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    if provider == "groq":
        return os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    return "claude-haiku-4-5-20251001"


async def chamar_anthropic(
    prompt: str,
    *,
    max_tokens: int = 512,
    timeout: float = 15.0,
    max_retries: int = 2,
    backoff_base: float = 1.0,
) -> str:
    """Chama o provedor de IA ativo (Anthropic, Gemini Free Tier, Groq ou Ollama) com failover em modo auto.

    Mantém o nome `chamar_anthropic` por compatibilidade com os serviços existentes.
    Levanta ValueError se nenhuma credencial/URL do provedor ativo estiver configurada.
    """
    explicit = os.getenv("IA_PROVIDER", "auto").strip().lower()
    if explicit and explicit != "auto":
        return await _chamar_provider(
            explicit,
            prompt,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            backoff_base=backoff_base,
        )

    candidatos = [
        p
        for p, env_var in (
            ("anthropic", "ANTHROPIC_API_KEY"),
            ("gemini", "GEMINI_API_KEY"),
            ("groq", "GROQ_API_KEY"),
            ("ollama", "OLLAMA_BASE_URL"),
        )
        if os.getenv(env_var, "").strip()
    ]
    if not candidatos:
        raise ValueError("Nenhuma chave/URL de provedor de IA configurada")

    ultimo_erro: Exception | None = None
    for provider in candidatos:
        try:
            return await _chamar_provider(
                provider,
                prompt,
                max_tokens=max_tokens,
                timeout=timeout,
                max_retries=max_retries,
                backoff_base=backoff_base,
            )
        except Exception as exc:
            ultimo_erro = exc
            continue
    raise ultimo_erro or RuntimeError("Falha ao chamar provedores de IA")


chamar_ia = chamar_anthropic
