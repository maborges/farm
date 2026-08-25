from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from core.config import settings


class BalancaServiceUnavailable(RuntimeError):
    pass


class BalancaServiceClient:
    """Adapter HTTP do AgroSaaS para o serviço Balança independente."""

    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret

    @classmethod
    def from_settings(cls) -> "BalancaServiceClient":
        """Cria o conector usando a configuração obrigatória do AgroSaaS.

        Raises:
            BalancaServiceUnavailable: quando a integração não foi configurada.
        """
        if not all((settings.balanca_service_url, settings.balanca_service_client_id, settings.balanca_service_client_secret)):
            raise BalancaServiceUnavailable("Integração com o serviço Balança não configurada.")
        return cls(
            settings.balanca_service_url,
            settings.balanca_service_client_id,
            settings.balanca_service_client_secret,
        )

    def _headers(self, tenant_id: str) -> dict[str, str]:
        return {
            "content-type": "application/json",
            "X-Tenant-ID": tenant_id,
            "X-Balanca-Client-ID": self.client_id,
            "X-Balanca-Client-Secret": self.client_secret,
        }

    async def _post(self, path: str, tenant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{self.base_url}{path}",
                    headers=self._headers(tenant_id),
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise BalancaServiceUnavailable("Serviço Balança indisponível.") from exc
        if response.is_error:
            raise BalancaServiceUnavailable(
                f"Serviço Balança recusou a operação ({response.status_code})."
            )
        return response.json()

    async def register_client(self, tenant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/v1/clients", tenant_id, payload)

    async def create_order(self, tenant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/v1/orders", tenant_id, payload)

    async def create_operator(self, tenant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/v1/operators", tenant_id, payload)

    async def list_operators(self, tenant_id: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.base_url}/v1/operators",
                    headers=self._headers(tenant_id),
                )
        except httpx.HTTPError as exc:
            raise BalancaServiceUnavailable("Serviço Balança indisponível.") from exc
        if response.is_error:
            raise BalancaServiceUnavailable(
                f"Serviço Balança recusou a operação ({response.status_code})."
            )
        return response.json()

    async def revoke_operator(self, tenant_id: str, operator_id: str) -> dict[str, Any]:
        return await self._post(f"/v1/operators/{operator_id}/revoke", tenant_id, {})

    @staticmethod
    def operator_response_payload(data: dict[str, Any]) -> dict[str, Any]:
        pessoa_id = data.get("pessoa_ref")
        try:
            import uuid
            pessoa_id = str(uuid.UUID(pessoa_id)) if pessoa_id else None
        except (ValueError, TypeError):
            pessoa_id = None
        return {
            "id": data["id"],
            "codigo_operador": data["codigo"],
            "pessoa_id": pessoa_id,
            "nome_exibicao": data["nome_exibicao"],
            "status": data["status"],
            "created_at": data["created_at"],
        }

    @staticmethod
    def order_response_payload(data: dict[str, Any]) -> dict[str, Any]:
        created_at = data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return {
            "id": data["id"],
            "origem_tipo": "OUTRO",
            "origem_id": None,
            "sistema_cliente": data["sistema_cliente"],
            "tenant_cliente_id": data["tenant_cliente_id"],
            "referencia_externa": data["referencia_externa"],
            "correlation_id": data["correlation_id"],
            "subject_type": data["subject_type"],
            "tipo_pesagem": data["tipo_pesagem"],
            "status": data["status"],
            "contexto": data.get("contexto", {}),
            "produto_id": None,
            "produto_tipo": None,
            "tipo_volume": None,
            "quantidade_volumes": None,
            "data_agendada": None,
            "numero_documento_fiscal": None,
            "peso_liquido_kg": data.get("peso_liquido_kg"),
            "dispositivo_id": None,
            "concluida_em": data.get("concluida_em"),
            "created_at": created_at,
            "updated_at": created_at,
        }
