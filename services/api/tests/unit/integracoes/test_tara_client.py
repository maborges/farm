import hashlib
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from integracoes.tara.client import TaraApiError, TaraClient


def _client() -> TaraClient:
    return TaraClient("https://tara.example", "client-1", "secret-1")


def _client_without_tenant_header() -> TaraClient:
    return TaraClient("https://tara.example", "client-1", "secret-1")


@pytest.mark.asyncio
async def test_client_envia_headers_tara_e_idempotency_key() -> None:
    response = httpx.Response(201, json={"id": "order-1"}, request=httpx.Request("POST", "https://tara.example/v1/orders"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response) as request:
        payload = {
            "client_system": "agrosaas",
            "client_tenant_id": "tenant-a",
            "external_reference": "stable-1",
            "correlation_id": "corr-1",
        }
        await _client().create_order(payload)
    headers = request.call_args.kwargs["headers"]
    assert headers["X-Balanca-Client-ID"] == "client-1"
    assert headers["X-Balanca-Client-Secret"] == "secret-1"
    canonical = json.dumps(["agrosaas", "tenant-a", "stable-1"], ensure_ascii=False, separators=(",", ":"))
    assert headers["Idempotency-Key"] == f"tara-order:{hashlib.sha256(canonical.encode()).hexdigest()}"


def test_order_idempotency_key_is_qualified_by_system_tenant_and_reference() -> None:
    identity = {"client_system": "erp-a", "client_tenant_id": "tenant-a", "external_reference": "REF:100"}
    original = TaraClient.order_idempotency_key(identity)
    assert TaraClient.order_idempotency_key(identity) == original
    assert TaraClient.order_idempotency_key({**identity, "client_system": "erp-b"}) != original
    assert TaraClient.order_idempotency_key({**identity, "client_tenant_id": "tenant-b"}) != original
    assert TaraClient.order_idempotency_key({**identity, "external_reference": "REF:101"}) != original


@pytest.mark.asyncio
async def test_client_nao_retrya_erro_de_credencial() -> None:
    response = httpx.Response(401, json={"detail": "invalid"}, request=httpx.Request("GET", "https://tara.example/v1/events"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response) as request:
        with pytest.raises(TaraApiError) as error:
            await _client().list_events()
    assert error.value.status_code == 401
    assert request.await_count == 1


@pytest.mark.asyncio
async def test_client_expoe_mensagem_de_credencial_nao_autorizada() -> None:
    response = httpx.Response(403, json={"detail": "scope ausente"}, request=httpx.Request("GET", "https://tara.example/v1/weighings"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        with pytest.raises(TaraApiError, match="não autorizado") as error:
            await _client().list_weighings(limit=1)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_client_projeta_operador_com_idempotencia_externa() -> None:
    response = httpx.Response(201, json={"id": "operator-1"}, request=httpx.Request("POST", "https://tara.example/v1/client/operators"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response) as request:
        await _client().create_operator({"external_id": "operador-123", "display_name": "João"})
    assert request.call_args.kwargs["headers"]["Idempotency-Key"] == "operador-123"
    assert request.call_args.kwargs["json"] == {
        "codigo": "operador-123",
        "nome_exibicao": "João",
        "identificador_externo": "operador-123",
    }


@pytest.mark.asyncio
async def test_client_revoga_operador_por_endpoint_publico() -> None:
    response = httpx.Response(200, json={"status": "REVOGADO"}, request=httpx.Request("POST", "https://tara.example/v1/client/operators/operator-1/revoke"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response) as request:
        await _client().revoke_operator("operator-1")
    assert request.call_args.args[0] == "POST"
    assert request.call_args.args[1].endswith("/v1/client/operators/operator-1/revoke")


@pytest.mark.asyncio
async def test_client_testa_conexao_com_consulta_leve() -> None:
    response = httpx.Response(200, json={"items": [], "next_cursor": None}, request=httpx.Request("GET", "https://tara.example/v1/weighings"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response) as request:
        await _client().test_connection()
    assert request.call_args.args[1].endswith("/v1/weighings")
    assert request.call_args.kwargs["params"] == {"limit": "1"}


@pytest.mark.asyncio
async def test_client_nao_envia_tenant_no_header() -> None:
    response = httpx.Response(200, json={"items": []}, request=httpx.Request("GET", "https://tara.example/v1/weighings"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response) as request:
        await _client_without_tenant_header().list_weighings(limit=1)
    assert "X-Tenant-ID" not in request.call_args.kwargs["headers"]
    assert request.call_args.kwargs["headers"]["X-Balanca-Client-ID"] == "client-1"
