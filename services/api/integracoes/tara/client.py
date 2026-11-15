"""Cliente HTTP versionado da Plataforma TARA."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

import httpx


class TaraApiError(RuntimeError):
    """Erro sanitizado retornado pela API TARA."""

    def __init__(self, status_code: int, detail: str = "Erro na Plataforma TARA") -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class TaraClient:
    """Implementa somente os endpoints HTTP públicos e versionados do Pondaxis."""

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
                    raise TaraApiError(503, "Plataforma Pondaxis indisponível") from exc
                await asyncio.sleep(2**attempt)
                continue
            if response.status_code not in (429,) and response.status_code < 500:
                if response.is_error:
                    try:
                        body = response.json()
                    except ValueError:
                        body = {}
                    detail = body.get("detail") if isinstance(body, dict) else None
                    if response.status_code == 401:
                        message = "Credencial do sistema cliente não autenticada no Pondaxis."
                    elif response.status_code == 403:
                        message = "Sistema cliente não autorizado a executar esta operação no Pondaxis."
                    else:
                        message = detail or f"Pondaxis recusou a operação ({response.status_code})"
                    raise TaraApiError(response.status_code, message)
                return response.json() if response.content else None
            if not retryable or attempt == 2:
                raise TaraApiError(response.status_code, f"Falha temporária do Pondaxis ({response.status_code})")
            await asyncio.sleep(2**attempt)
        raise TaraApiError(503, "Plataforma Pondaxis indisponível")

    async def register_client(self, payload: dict[str, Any]) -> Any:
        """Registra o sistema consumidor de forma idempotente."""
        key = f"{payload.get('sistema_cliente')}:{payload.get('tenant_cliente_id')}"
        return await self._request("POST", "/v1/clients", json=payload, idempotency_key=key)

    async def create_order(self, payload: dict[str, Any]) -> Any:
        """Cria ou recupera uma Ordem identificada pelas referências estáveis."""
        key = self.order_idempotency_key(payload)
        return await self._request("POST", "/v1/orders", json=payload, idempotency_key=key)

    @staticmethod
    def order_idempotency_key(payload: dict[str, Any]) -> str:
        """Qualifica a idempotência pela identidade externa completa.

        A API Pondaxis também escopa idempotência pela Conta autenticada; o digest
        mantém o header curto e evita ambiguidades quando referências contêm `:`.
        """
        identity = [
            payload.get("client_system"),
            payload.get("client_tenant_id"),
            payload.get("external_reference"),
        ]
        if all(isinstance(value, str) and value for value in identity):
            canonical = json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            return f"tara-order:{digest}"
        return str(payload.get("correlation_id") or "tara-order:missing-identity")

    async def create_operator(self, payload: dict[str, Any]) -> Any:
        """Registra uma projeção de operador usando somente a API pública."""
        key = str(payload.get("external_id") or payload.get("identificador_externo"))
        external_id = str(payload.get("external_id") or payload.get("identificador_externo") or "").strip()
        display_name = str(payload.get("display_name") or payload.get("nome_exibicao") or "").strip()
        tara_payload = {
            "codigo": external_id,
            "nome_exibicao": display_name,
            "identificador_externo": external_id or None,
        }
        return await self._request("POST", "/v1/client/operators", json=tara_payload, idempotency_key=key)

    async def list_operators(self) -> Any:
        """Consulta operadores disponíveis para o cliente na Conta Pondaxis."""
        return await self._request("GET", "/v1/client/operators")

    async def revoke_operator(self, operator_id: str) -> Any:
        """Revoga um operador pela referência pública retornada pelo Pondaxis."""
        return await self._request("POST", f"/v1/client/operators/{operator_id}/revoke", json={})

    async def get_order(self, order_id: str) -> Any:
        """Consulta uma Ordem por seu identificador Pondaxis."""
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
        """Ativa uma Estação através do endpoint público do Pondaxis."""
        return await self._request("POST", "/v1/stations/activate", json=payload)
