# ruff: noqa: S105, S106, UP017
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

import httpx
import pytest

from integracoes.sankhya.services.auth_service import (
    SankhyaConnectionData,
    SankhyaGatewayAuthService,
    SankhyaGatewayToken,
)
from integracoes.security import encrypt_integration_secret


def _gateway_config() -> SankhyaConnectionData:
    return SankhyaConnectionData(
        environment="producao",
        api_base_url="https://gateway.example/api",
        auth_url="https://gateway.example/authenticate",
        client_id="client-123",
        client_secret=encrypt_integration_secret("client-secret"),
        x_token=encrypt_integration_secret("x-token"),
    )


def _legacy_gateway_login_config() -> SankhyaConnectionData:
    return SankhyaConnectionData(
        environment="producao",
        api_base_url="https://gateway.example/api",
        auth_url="https://gateway.example/login",
        username="legacy-user",
        password=encrypt_integration_secret("legacy-password"),
        token=encrypt_integration_secret("legacy-token"),
        appkey=encrypt_integration_secret("legacy-appkey"),
    )


@pytest.mark.asyncio
async def test_gateway_auth_monta_headers_e_body_corretos() -> None:
    SankhyaGatewayAuthService.clear_cache()
    config = _gateway_config()
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = parse_qs(request.content.decode())
        return httpx.Response(200, json={"access_token": "token-abc", "expires_in": 120})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SankhyaGatewayAuthService(config)

    assert service.auth_model() == "gateway_oauth_client_credentials"
    token = await service.authenticate(client)

    await client.aclose()

    assert token == "token-abc"
    assert captured["url"] == "https://gateway.example/authenticate"
    assert captured["headers"]["x-token"] == "x-token"
    assert captured["headers"]["content-type"].startswith(
        "application/x-www-form-urlencoded"
    )
    assert captured["body"]["client_id"] == ["client-123"]
    assert captured["body"]["client_secret"] == ["client-secret"]
    assert captured["body"]["grant_type"] == ["client_credentials"]


@pytest.mark.asyncio
async def test_gateway_legacy_login_auth_monta_headers_e_le_bearer_token() -> None:
    SankhyaGatewayAuthService.clear_cache()
    config = _legacy_gateway_login_config()
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = request.content
        return httpx.Response(200, json={"bearerToken": "legacy-token-abc"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SankhyaGatewayAuthService(config)

    assert service.auth_model() == "gateway_legacy_login"
    description = service.describe()
    assert description["token_mask"] == "••••••••"
    assert description["appkey_mask"] == "••••••••"
    token = await service.authenticate(client)

    await client.aclose()

    assert token == "legacy-token-abc"
    assert captured["url"] == "https://gateway.example/login"
    assert "x-token" not in captured["headers"]
    assert captured["headers"]["token"] == "legacy-token"
    assert captured["headers"]["appkey"] == "legacy-appkey"
    assert captured["headers"]["username"] == "legacy-user"
    assert captured["headers"]["password"] == "legacy-password"
    assert captured["body"] == b""


@pytest.mark.asyncio
async def test_gateway_auth_usa_cache_ate_expirar() -> None:
    SankhyaGatewayAuthService.clear_cache()
    config = _gateway_config()
    calls: list[int] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json={"access_token": "token-cache", "expires_in": 120})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SankhyaGatewayAuthService(config)

    first = await service.authenticate(client)
    second = await service.authenticate(client)

    await client.aclose()

    assert first == second == "token-cache"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_gateway_auth_renova_quando_cache_expira() -> None:
    SankhyaGatewayAuthService.clear_cache()
    config = _gateway_config()
    cache_key = SankhyaGatewayAuthService.cache_key_for(config)
    SankhyaGatewayAuthService._token_cache[cache_key] = SankhyaGatewayToken(
        access_token="expired",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    calls: list[int] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json={"access_token": "token-novo", "expires_in": 120})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SankhyaGatewayAuthService(config)

    token = await service.authenticate(client)

    await client.aclose()

    assert token == "token-novo"
    assert len(calls) == 1


def test_gateway_config_incompleta_rejeita_auth() -> None:
    config = SankhyaConnectionData(
        environment="producao",
        api_base_url="https://gateway.example/api",
        auth_url="https://gateway.example/authenticate",
        client_id="client-123",
        client_secret=encrypt_integration_secret("client-secret"),
    )

    service = SankhyaGatewayAuthService(config)

    with pytest.raises(ValueError, match="sankhya_x_token"):
        service.validate_gateway_config()


def test_legacy_nao_e_fluxo_padrao_quando_gateway_esta_disponivel() -> None:
    config = SankhyaConnectionData(
        environment="producao",
        api_base_url="https://gateway.example/api",
        auth_url="https://gateway.example/authenticate",
        client_id="client-123",
        client_secret=encrypt_integration_secret("client-secret"),
        x_token=encrypt_integration_secret("x-token"),
        ws_url="https://legacy.example/ws",
        username="legacy-user",
        password=encrypt_integration_secret("legacy-pass"),
    )

    service = SankhyaGatewayAuthService(config)

    assert service.auth_model() == "gateway_oauth_client_credentials"
