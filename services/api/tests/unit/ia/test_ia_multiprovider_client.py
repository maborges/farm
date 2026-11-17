from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ia.anthropic_client import (
    chamar_anthropic,
    get_ia_model,
    get_ia_provider,
    has_ia_configured,
)


def _mock_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


@pytest.mark.asyncio
async def test_auto_detect_gemini_free_tier():
    env = {"IA_PROVIDER": "auto", "ANTHROPIC_API_KEY": "", "GEMINI_API_KEY": "gm-free-key", "IA_MODEL": ""}
    mock_post = AsyncMock(
        return_value=_mock_response({"candidates": [{"content": {"parts": [{"text": "Resposta Gemini"}]}}]})
    )
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = mock_post

    with patch.dict("os.environ", env, clear=False), patch("ia.anthropic_client.httpx.AsyncClient", return_value=mock_client):
        assert get_ia_provider() == "gemini"
        assert get_ia_model() == "gemini-flash-latest"
        assert has_ia_configured() is True
        texto = await chamar_anthropic("Teste prompt")

    assert texto == "Resposta Gemini"
    assert "generativelanguage.googleapis.com" in mock_post.call_args.args[0]


@pytest.mark.asyncio
async def test_auto_detect_groq_free_tier():
    env = {"IA_PROVIDER": "auto", "ANTHROPIC_API_KEY": "", "GEMINI_API_KEY": "", "GROQ_API_KEY": "gsk-free", "IA_MODEL": ""}
    mock_post = AsyncMock(
        return_value=_mock_response({"choices": [{"message": {"content": "Resposta Groq"}}]})
    )
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = mock_post

    with patch.dict("os.environ", env, clear=False), patch("ia.anthropic_client.httpx.AsyncClient", return_value=mock_client):
        assert get_ia_provider() == "groq"
        assert get_ia_model() == "openai/gpt-oss-20b"
        texto = await chamar_anthropic("Teste prompt")

    assert texto == "Resposta Groq"
    assert "api.groq.com" in mock_post.call_args.args[0]


@pytest.mark.asyncio
async def test_auto_detect_gemini_ignora_ia_model_legado_claude():
    env = {
        "IA_PROVIDER": "auto",
        "ANTHROPIC_API_KEY": "",
        "GEMINI_API_KEY": "gm-free-key",
        "IA_MODEL": "claude-haiku-4-5-20251001",
    }
    with patch.dict("os.environ", env, clear=False):
        assert get_ia_provider() == "gemini"
        assert get_ia_model() == "gemini-flash-latest"


@pytest.mark.asyncio
async def test_auto_detect_openai():
    env = {
        "IA_PROVIDER": "auto",
        "ANTHROPIC_API_KEY": "",
        "OPENAI_API_KEY": "sk-openai-test",
        "GEMINI_API_KEY": "",
        "GROQ_API_KEY": "",
        "IA_MODEL": "",
    }
    mock_post = AsyncMock(
        return_value=_mock_response({"choices": [{"message": {"content": "Resposta OpenAI"}}]})
    )
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = mock_post

    with patch.dict("os.environ", env, clear=False), patch("ia.anthropic_client.httpx.AsyncClient", return_value=mock_client):
        assert get_ia_provider() == "openai"
        assert get_ia_model() == "gpt-4o-mini"
        texto = await chamar_anthropic("Teste prompt")

    assert texto == "Resposta OpenAI"
    assert "api.openai.com" in mock_post.call_args.args[0]


@pytest.mark.asyncio
async def test_sem_chave_configurada_levanta_value_error():
    env = {
        "IA_PROVIDER": "auto",
        "ANTHROPIC_API_KEY": "",
        "GEMINI_API_KEY": "",
        "GROQ_API_KEY": "",
        "OLLAMA_BASE_URL": "",
    }
    with patch.dict("os.environ", env, clear=False):
        assert has_ia_configured() is False
        with pytest.raises(ValueError):
            await chamar_anthropic("Teste")
