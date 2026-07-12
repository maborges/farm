# ruff: noqa: S105, S106
from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import Column, Table
from sqlalchemy import Uuid as UUIDType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import Base
from integracoes.sankhya.models import SankhyaConfig
from integracoes.sankhya.services.auth_service import (
    SankhyaGatewayAuthService,
    SankhyaGatewayConnectionDiagnostic,
)
from integracoes.sankhya.services.sync_service import SankhyaSyncService
from integracoes.security import encrypt_integration_secret

if "domain_event_outbox" not in Base.metadata.tables:
    Table(
        "domain_event_outbox",
        Base.metadata,
        Column("id", UUIDType(as_uuid=True), primary_key=True),
    )


@pytest_asyncio.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: SankhyaConfig.__table__.create(sync_conn))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as current:
        yield current

    await engine.dispose()


def _gateway_config() -> SankhyaConfig:
    return SankhyaConfig(
        tenant_id="tenant-gateway",
        environment="producao",
        api_base_url="https://gateway.example/api",
        auth_url="https://gateway.example/authenticate",
        client_id="client-123",
        client_secret=encrypt_integration_secret("client-secret"),
        x_token=encrypt_integration_secret("x-token"),
        sync_interval=900,
        ativo=True,
    )


def _legacy_login_config() -> SankhyaConfig:
    return SankhyaConfig(
        tenant_id="tenant-legacy-login",
        environment="producao",
        api_base_url="https://gateway.example/api",
        auth_url="https://gateway.example/login",
        username="legacy-user",
        password=encrypt_integration_secret("legacy-password"),
        token=encrypt_integration_secret("legacy-token"),
        appkey=encrypt_integration_secret("legacy-appkey"),
        sync_interval=900,
        ativo=True,
    )


@pytest.mark.asyncio
async def test_gateway_test_connection_chama_authenticate_e_sanitiza_resposta() -> None:
    SankhyaGatewayAuthService.clear_cache()
    config = _gateway_config()
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "access_token": "token-abc",
                "expires_at": "2026-07-05T15:00:00+00:00",
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SankhyaGatewayAuthService(config)

    diagnostic = await service.test_connection(client)

    await client.aclose()

    assert captured["url"] == "https://gateway.example/authenticate"
    assert captured["headers"]["x-token"] == "x-token"
    assert captured["body"]["client_id"] == "client-123"
    assert captured["body"]["client_secret"] == "client-secret"
    assert captured["body"]["grant_type"] == "client_credentials"
    assert diagnostic.sucesso is True
    assert diagnostic.token_obtido is True
    assert diagnostic.token_expires_at == datetime(2026, 7, 5, 15, 0, tzinfo=timezone.utc)
    assert diagnostic.client_id_mask == "••••••••"
    assert diagnostic.x_token_mask == "••••••••"
    assert SankhyaGatewayAuthService.cache_key_for(config) not in SankhyaGatewayAuthService._token_cache


@pytest.mark.asyncio
async def test_gateway_legacy_login_test_connection_chama_login_e_sanitiza_resposta() -> None:
    SankhyaGatewayAuthService.clear_cache()
    config = _legacy_login_config()
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content
        return httpx.Response(
            200,
            json={
                "bearerToken": "legacy-token-abc",
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SankhyaGatewayAuthService(config)

    diagnostic = await service.test_connection(client)

    await client.aclose()

    assert captured["url"] == "https://gateway.example/login"
    assert "x-token" not in captured["headers"]
    assert captured["headers"]["token"] == "legacy-token"
    assert captured["headers"]["appkey"] == "legacy-appkey"
    assert captured["headers"]["username"] == "legacy-user"
    assert captured["headers"]["password"] == "legacy-password"
    assert captured["body"] == b""
    assert diagnostic.sucesso is True
    assert diagnostic.token_obtido is True
    assert diagnostic.auth_model == "gateway_legacy_login"


@pytest.mark.asyncio
async def test_sync_service_testar_conexao_nao_persiste_estado_do_teste(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SankhyaSyncService(session)
    config = _gateway_config()
    session.add(config)
    await session.commit()

    async def fake_test_connection(self, client=None):  # type: ignore[no-untyped-def]
        return SankhyaGatewayConnectionDiagnostic(
            sucesso=True,
            mensagem="Autenticação Sankhya Gateway concluída com sucesso",
            ambiente="producao",
            base_url="https://gateway.example/api",
            auth_url="https://gateway.example/authenticate",
            client_id_mask="••••••••",
            x_token_mask="••••••••",
            token_obtido=True,
            token_expires_at=datetime(2026, 7, 5, 15, 0, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(SankhyaGatewayAuthService, "test_connection", fake_test_connection)

    result = await service.testar_conexao("tenant-gateway")
    stored = await service.get_config("tenant-gateway")

    assert result.sucesso is True
    assert result.token_obtido is True
    assert result.base_url == "https://gateway.example/api"
    assert stored is not None
    assert stored.ultimo_teste is None
    assert stored.teste_status is None


@pytest.mark.asyncio
async def test_sync_service_testar_conexao_retorna_falha_sanitizada_em_config_incompleta(
    session: AsyncSession,
) -> None:
    service = SankhyaSyncService(session)
    config = SankhyaConfig(
        tenant_id="tenant-incompleto",
        environment="sandbox",
        api_base_url="https://gateway.example/api",
        auth_url="https://gateway.example/authenticate",
        client_id="client-123",
        client_secret=encrypt_integration_secret("client-secret"),
        sync_interval=900,
        ativo=True,
    )
    session.add(config)
    await session.commit()

    result = await service.testar_conexao("tenant-incompleto")

    assert result.sucesso is False
    assert result.token_obtido is False
    assert result.client_id_mask == "••••••••"
    assert result.x_token_mask is None
    assert "sankhya_x_token" in result.mensagem
