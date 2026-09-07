"""Cliente HTTP versionado da Plataforma TARA."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx


class TaraApiError(RuntimeError):
    """Erro sanitizado retornado pela API TARA."""

    def __init__(self, status_code: int, detail: str = "Erro na Plataforma TARA") -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class TaraClient:
    """Implementa somente os endpoints HTTP públicos e versionados da TARA."""

    def __init__(self, base_url: str, client_id: str, client_secret: str, timeout: float = 15) -> None:
        self.base_url = str(base_url).rstrip("/")
        self.client_id, self.client_secret = client_id, client_secret
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "X-Balanca-Client-ID": self.client_id, "X-Balanca-Client-Secret": self.client_secret}
        return headers

    async def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None, params: dict[str, str] | None = None, idempotency_key: str | None = None) -> Any:
        """Executa requisição com retry apenas para falhas transitórias."""
        retryable = method == "GET" or bool(idempotency_key)
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as http:
                    headers = self._headers()
                    if idempotency_key:
                        headers["Idempotency-Key"] = idempotency_key
                    response = await http.request(method, f"{self.base_url}{path}", headers=headers, json=json, params=params)
            except httpx.HTTPError as exc:
                if not retryable or attempt == 2:
                    raise TaraApiError(503, "Plataforma TARA indisponível") from exc
                await asyncio.sleep(2**attempt)
                continue
            if response.status_code not in (429,) and response.status_code < 500:
                if response.is_error:
                    raise TaraApiError(response.status_code, f"TARA recusou a operação ({response.status_code})")
                return response.json() if response.content else None
            if not retryable or attempt == 2:
                raise TaraApiError(response.status_code, f"Falha temporária da TARA ({response.status_code})")
            await asyncio.sleep(2**attempt)
        raise TaraApiError(503, "Plataforma TARA indisponível")

    async def register_client(self, payload: dict[str, Any]) -> Any:
        """Registra o sistema consumidor de forma idempotente."""
        key = f"{payload.get('sistema_cliente')}:{payload.get('tenant_cliente_id')}"
        return await self._request("POST", "/v1/clients", json=payload, idempotency_key=key)

    async def create_order(self, payload: dict[str, Any]) -> Any:
        """Cria ou recupera uma Ordem identificada pelas referências estáveis."""
        key = str(payload.get("external_reference") or payload.get("correlation_id"))
        return await self._request("POST", "/v1/orders", json=payload, idempotency_key=key)

    async def create_operator(self, payload: dict[str, Any]) -> Any:
        """Registra uma projeção de operador usando somente a API pública."""
        key = str(payload.get("external_id") or payload.get("identificador_externo"))
        return await self._request("POST", "/v1/operators", json=payload, idempotency_key=key)

    async def list_operators(self) -> Any:
        """Consulta operadores disponíveis para o cliente na Conta TARA."""
        return await self._request("GET", "/v1/operators")

    async def revoke_operator(self, operator_id: str) -> Any:
        """Revoga um operador pela referência pública retornada pela TARA."""
        return await self._request("POST", f"/v1/operators/{operator_id}/revoke", json={})

    async def get_order(self, order_id: str) -> Any:
        """Consulta uma Ordem por seu identificador TARA."""
        return await self._request("GET", f"/v1/orders/{order_id}")

    async def list_weighings(self, limit: int = 100, cursor: str | None = None) -> Any:
        """Consulta uma página sem interpretar o cursor opaco."""
        params = {"limit": str(limit)}
        if cursor is not None:
            params["cursor"] = cursor
        return await self._request("GET", "/v1/weighings", params=params)

    async def list_events(self, limit: int = 100, cursor: str | None = None) -> Any:
        """Consulta eventos para recuperação e reconciliação."""
        params = {"limit": str(limit)}
        if cursor is not None:
            params["cursor"] = cursor
        return await self._request("GET", "/v1/events", params=params)

    async def test_connection(self) -> Any:
        """Valida credenciais e alcance da Conta por uma consulta leve."""
        return await self._request("GET", "/v1/weighings", params={"limit": "1"})

    async def get_webhook(self) -> Any:
        """Consulta a configuração de webhook da Conta."""
        return await self._request("GET", "/v1/webhooks")

    async def manage_webhook(self, payload: dict[str, Any]) -> Any:
        """Cria ou atualiza o webhook da Conta."""
        return await self._request("PUT", "/v1/webhooks", json=payload)

    async def replay_webhook(self, payload: dict[str, Any]) -> Any:
        """Solicita reprocessamento de entrega sem duplicar negócio local."""
        return await self._request("POST", "/v1/webhooks/replay", json=payload)

    async def activate_station(self, payload: dict[str, Any]) -> Any:
        """Ativa uma Estação através do endpoint público da TARA."""
        return await self._request("POST", "/v1/stations/activate", json=payload)
