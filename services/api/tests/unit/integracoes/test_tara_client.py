from unittest.mock import AsyncMock, patch

import httpx
import pytest

from integracoes.tara.client import TaraApiError, TaraClient


def _client() -> TaraClient:
    return TaraClient("https://tara.example", "account-1", "client-1", "secret-1")


@pytest.mark.asyncio
async def test_client_envia_headers_tara_e_idempotency_key() -> None:
    response = httpx.Response(201, json={"id": "order-1"}, request=httpx.Request("POST", "https://tara.example/v1/orders"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response) as request:
        await _client().create_order({"external_reference": "stable-1", "correlation_id": "corr-1"})
    headers = request.call_args.kwargs["headers"]
    assert headers["X-Tenant-ID"] == "account-1"
    assert headers["X-Balanca-Client-ID"] == "client-1"
    assert headers["X-Balanca-Client-Secret"] == "secret-1"
    assert headers["Idempotency-Key"] == "stable-1"


@pytest.mark.asyncio
async def test_client_nao_retrya_erro_de_credencial() -> None:
    response = httpx.Response(401, json={"detail": "invalid"}, request=httpx.Request("GET", "https://tara.example/v1/events"))
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response) as request:
        with pytest.raises(TaraApiError) as error:
            await _client().list_events()
    assert error.value.status_code == 401
    assert request.await_count == 1
