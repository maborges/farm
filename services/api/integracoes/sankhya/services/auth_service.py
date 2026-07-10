"""Autenticação gateway da Sankhya."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

import httpx

from integracoes.sankhya.models import SankhyaConfig
from integracoes.security import decrypt_integration_secret, mask_integration_secret


@dataclass(slots=True)
class SankhyaGatewayToken:
    access_token: str
    expires_at: datetime

    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < self.expires_at


@dataclass(slots=True)
class SankhyaGatewayConnectionDiagnostic:
    sucesso: bool
    mensagem: str
    ambiente: str | None
    base_url: str | None
    auth_url: str | None
    client_id_mask: str | None
    x_token_mask: str | None
    token_obtido: bool
    token_expires_at: datetime | None
    auth_model: str = "gateway_oauth_client_credentials"

    def as_dict(self) -> dict[str, Any]:
        return {
            "sucesso": self.sucesso,
            "mensagem": self.mensagem,
            "ambiente": self.ambiente,
            "base_url": self.base_url,
            "auth_url": self.auth_url,
            "client_id_mask": self.client_id_mask,
            "x_token_mask": self.x_token_mask,
            "token_obtido": self.token_obtido,
            "token_expires_at": self.token_expires_at,
            "auth_model": self.auth_model,
        }


class SankhyaGatewayAuthService:
    """Obtém access_token do Gateway Sankhya sem expor segredos."""

    _token_cache: ClassVar[dict[str, SankhyaGatewayToken]] = {}

    def __init__(self, config: SankhyaConfig) -> None:
        self.config = config

    @classmethod
    def cache_key_for(cls, config: SankhyaConfig) -> str:
        return "|".join(
            [
                (config.environment or "").strip().lower(),
                (config.auth_url or config.ws_url or "").rstrip("/"),
                (config.api_base_url or config.ws_url or "").rstrip("/"),
                (config.client_id or "").strip(),
                (decrypt_integration_secret(config.client_secret) or "").strip(),
                (decrypt_integration_secret(config.x_token) or "").strip(),
                (decrypt_integration_secret(getattr(config, "token", None)) or "").strip(),
                (decrypt_integration_secret(getattr(config, "appkey", None)) or "").strip(),
            ]
        )

    @classmethod
    def clear_cache(cls) -> None:
        cls._token_cache.clear()

    def is_gateway_oauth_configured(self) -> bool:
        return all(
            [
                self.config.api_base_url,
                self.config.auth_url,
                self.config.client_id,
                decrypt_integration_secret(self.config.client_secret),
                decrypt_integration_secret(self.config.x_token),
            ]
        )

    def is_gateway_legacy_login_configured(self) -> bool:
        return all(
            [
                self.config.auth_url or self.config.api_base_url,
                self.config.username,
                decrypt_integration_secret(getattr(self.config, "token", None)),
                decrypt_integration_secret(getattr(self.config, "appkey", None)),
                decrypt_integration_secret(self.config.password),
            ]
        )

    def is_legacy_ws_basic_configured(self) -> bool:
        return all([self.config.ws_url, self.config.username, self.config.password])

    def is_legacy_configured(self) -> bool:
        return self.is_gateway_legacy_login_configured() or self.is_legacy_ws_basic_configured()

    def auth_model(self) -> str:
        if self.is_gateway_oauth_configured():
            return "gateway_oauth_client_credentials"
        if self.is_gateway_legacy_login_configured():
            return "gateway_legacy_login"
        if self.is_legacy_ws_basic_configured():
            return "legacy_ws_basic_auth"
        return "incomplete"

    def validation_auth_model(self) -> str:
        if self.is_gateway_oauth_configured():
            return "gateway_oauth_client_credentials"
        if self.is_gateway_legacy_login_configured():
            return "gateway_legacy_login"
        if any([getattr(self.config, "token", None), getattr(self.config, "appkey", None)]):
            return "gateway_legacy_login"
        if any(
            [
                self.config.api_base_url,
                self.config.auth_url,
                self.config.client_id,
                self.config.client_secret,
                self.config.x_token,
            ]
        ):
            return "gateway_oauth_client_credentials"
        if self.is_legacy_ws_basic_configured():
            return "legacy_ws_basic_auth"
        if any([self.config.ws_url, self.config.username, self.config.password]):
            return "legacy_ws_basic_auth"
        return "incomplete"

    def validate_legacy_config(self) -> None:
        if self.validation_auth_model() == "gateway_legacy_login":
            self.validate_gateway_legacy_login_config()
            return
        if self.validation_auth_model() == "legacy_ws_basic_auth":
            self.validate_legacy_basic_config()
            return
        raise ValueError("Configuração Sankhya LEGACY incompleta")

    def validate_gateway_config(self) -> None:
        missing: list[str] = []
        if not self.config.api_base_url:
            missing.append("sankhya_api_base_url")
        if not self.config.auth_url:
            missing.append("sankhya_auth_url")
        if not self.config.client_id:
            missing.append("sankhya_client_id")
        if not decrypt_integration_secret(self.config.client_secret):
            missing.append("sankhya_client_secret")
        if not decrypt_integration_secret(self.config.x_token):
            missing.append("sankhya_x_token")

        if missing:
            raise ValueError(
                "Configuração Sankhya Gateway incompleta: " + ", ".join(missing)
            )

    def validate_gateway_legacy_login_config(self) -> None:
        missing: list[str] = []
        if not (self.config.auth_url or self.config.api_base_url):
            missing.append("sankhya_auth_url")
        if not decrypt_integration_secret(getattr(self.config, "token", None)):
            missing.append("token")
        if not decrypt_integration_secret(getattr(self.config, "appkey", None)):
            missing.append("appkey")
        if not self.config.username:
            missing.append("username")
        if not decrypt_integration_secret(self.config.password):
            missing.append("password")
        if missing:
            raise ValueError(
                "Configuração Sankhya legacy login incompleta: " + ", ".join(missing)
            )

    def validate_legacy_basic_config(self) -> None:
        missing: list[str] = []
        if not self.config.ws_url:
            missing.append("ws_url")
        if not self.config.username:
            missing.append("username")
        if not self.config.password:
            missing.append("password")
        if missing:
            raise ValueError("Configuração Sankhya LEGACY incompleta: " + ", ".join(missing))

    def describe(self) -> dict[str, Any]:
        """Resumo mascarado para logs/diagnóstico."""

        return {
            "environment": self.config.environment,
            "auth_model": self.auth_model(),
            "api_base_url": self.config.api_base_url or self.config.ws_url,
            "auth_url": self.config.auth_url,
            "client_id": self.config.client_id,
            "client_secret_mask": mask_integration_secret(self.config.client_secret),
            "x_token_mask": mask_integration_secret(self.config.x_token),
            "token_mask": mask_integration_secret(getattr(self.config, "token", None)),
            "appkey_mask": mask_integration_secret(getattr(self.config, "appkey", None)),
            "ws_url": self.config.ws_url,
            "username": self.config.username,
            "password_mask": mask_integration_secret(self.config.password),
        }

    async def authenticate(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        cache_result: bool = True,
    ) -> str:
        """Obtém um access token, reutilizando cache até a expiração.

        Args:
            client: Cliente HTTP opcional injetado em testes.
            cache_result: Define se o token obtido deve ser armazenado em cache.

        Returns:
            Token de acesso emitido pelo Gateway Sankhya.

        Raises:
            ValueError: Quando a configuração Gateway está incompleta ou a resposta é inválida.
            httpx.HTTPError: Quando o Gateway responde com erro HTTP.
        """

        access_token, expires_at = await self._request_token(client, cache_result=cache_result)
        if cache_result:
            cache_key = self.cache_key_for(self.config)
            self._token_cache[cache_key] = SankhyaGatewayToken(
                access_token=access_token,
                expires_at=expires_at,
            )
        return access_token

    async def test_connection(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> SankhyaGatewayConnectionDiagnostic:
        """Executa um teste controlado do Gateway sem persistir resultado externo.

        Args:
            client: Cliente HTTP opcional injetado em testes.

        Returns:
            Snapshot sanitizado da tentativa de autenticação.
        """

        try:
            if self.validation_auth_model() == "gateway_oauth_client_credentials":
                self.validate_gateway_config()
            elif self.validation_auth_model() == "gateway_legacy_login":
                self.validate_gateway_legacy_login_config()
            elif self.validation_auth_model() == "legacy_ws_basic_auth":
                self.validate_legacy_basic_config()
            else:
                raise ValueError("Configuração Sankhya incompleta")
        except ValueError as exc:
            return self._build_diagnostic(False, str(exc), None)

        if self.validation_auth_model() == "legacy_ws_basic_auth":
            return self._build_diagnostic(
                True,
                "Configuração Sankhya LEGACY validada com sucesso",
                None,
            )

        try:
            _, expires_at = await self._request_token(client, cache_result=False)
        except ValueError as exc:
            return self._build_diagnostic(False, str(exc), None)
        except httpx.HTTPError:
            return self._build_diagnostic(
                False,
                "Falha ao autenticar no Gateway Sankhya",
                None,
            )

        return self._build_diagnostic(
            True,
            "Autenticação Sankhya Gateway concluída com sucesso",
            expires_at,
        )

    async def _request_token(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        cache_result: bool = False,
    ) -> tuple[str, datetime]:
        """Solicita o token de autenticação ao Gateway Sankhya.

        Args:
            client: Cliente HTTP opcional injetado em testes.
            cache_result: Mantido apenas para compatibilidade do fluxo de obtenção.

        Returns:
            Tupla com token de acesso e timestamp de expiração.

        Raises:
            ValueError: Quando a configuração Gateway está incompleta.
            httpx.HTTPError: Quando a requisição ao Gateway falha.
        """

        auth_model = self.validation_auth_model()
        if auth_model == "gateway_oauth_client_credentials":
            self.validate_gateway_config()
        elif auth_model == "gateway_legacy_login":
            self.validate_gateway_legacy_login_config()
        elif auth_model == "legacy_ws_basic_auth":
            self.validate_legacy_basic_config()
        else:
            raise ValueError("Configuração Sankhya incompleta")
        cache_key = self.cache_key_for(self.config)
        if cache_result:
            cached = self._token_cache.get(cache_key)
            if cached and cached.is_valid():
                return cached.access_token, cached.expires_at

        owns_client = client is None
        http_client = client or httpx.AsyncClient(timeout=60.0)
        try:
            response = await self._perform_authentication_request(http_client, auth_model=auth_model)
            response.raise_for_status()

            data = response.json()
            access_token = self._extract_access_token(data)
            expires_at = self._resolve_expiration(data)
            return access_token, expires_at
        finally:
            if owns_client:
                await http_client.aclose()

    async def _perform_authentication_request(
        self,
        http_client: httpx.AsyncClient,
        *,
        auth_model: str,
    ) -> httpx.Response:
        """Executa a chamada HTTP ao endpoint /authenticate.

        Args:
            http_client: Cliente HTTP já configurado.

        Returns:
            Resposta HTTP do Gateway Sankhya.
        """

        if auth_model == "gateway_legacy_login":
            endpoint = self.config.auth_url or f"{(self.config.api_base_url or self.config.ws_url or '').rstrip('/')}/login"
            headers = {
                "Accept": "application/json",
                "token": decrypt_integration_secret(getattr(self.config, "token", None)),
                "appkey": decrypt_integration_secret(getattr(self.config, "appkey", None)),
                "username": self.config.username or "",
                "password": decrypt_integration_secret(self.config.password),
            }
            return await http_client.post(endpoint, headers=headers)
        elif auth_model == "legacy_ws_basic_auth":
            raise ValueError("Configuração Sankhya LEGACY não utiliza fluxo de token")
        else:
            endpoint = self.config.auth_url or ""
            payloads = [
                (
                    "json",
                    {
                        "client_id": self.config.client_id,
                        "client_secret": decrypt_integration_secret(self.config.client_secret),
                        "grant_type": "client_credentials",
                    },
                ),
                (
                    "data",
                    {
                        "client_id": self.config.client_id,
                        "client_secret": decrypt_integration_secret(self.config.client_secret),
                        "grant_type": "client_credentials",
                    },
                ),
                (
                    "json",
                    {
                        "client_id": self.config.client_id,
                        "client_secret": decrypt_integration_secret(self.config.client_secret),
                    },
                ),
            ]
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Token": decrypt_integration_secret(self.config.x_token),
            }

        response: httpx.Response | None = None
        for index, (mode, payload) in enumerate(payloads):
            request_headers = dict(headers)
            if mode == "data":
                request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            request_kwargs: dict[str, Any] = {"headers": request_headers}
            if mode == "data":
                request_kwargs["data"] = payload
            else:
                request_kwargs["json"] = payload
            response = await http_client.post(endpoint, **request_kwargs)
            if response.status_code not in {400, 401, 415, 422} or index == len(payloads) - 1:
                break
        assert response is not None
        return response

    @staticmethod
    def _extract_access_token(data: dict[str, Any]) -> str:
        """Extrai o token de acesso da resposta de autenticação.

        Args:
            data: Payload JSON recebido do Gateway.

        Returns:
            Token de acesso.

        Raises:
            ValueError: Quando o payload não contém token válido.
        """

        access_token = (
            data.get("access_token")
            or data.get("bearerToken")
            or data.get("token")
            or data.get("accessToken")
        )
        if not access_token:
            raise ValueError("Resposta de autenticação Sankhya sem access_token")
        return str(access_token)

    def _build_diagnostic(
        self,
        sucesso: bool,
        mensagem: str,
        token_expires_at: datetime | None,
    ) -> SankhyaGatewayConnectionDiagnostic:
        """Monta a resposta sanitizada do teste de conexão."""

        return SankhyaGatewayConnectionDiagnostic(
            sucesso=sucesso,
            mensagem=mensagem,
            ambiente=self.config.environment,
            base_url=self.config.api_base_url or self.config.ws_url,
            auth_url=self.config.auth_url,
            client_id_mask=mask_integration_secret(self.config.client_id),
            x_token_mask=mask_integration_secret(self.config.x_token),
            token_obtido=sucesso,
            token_expires_at=token_expires_at,
            auth_model=self.auth_model(),
        )

    def build_request_headers(self, access_token: str) -> dict[str, str]:
        """Headers padrão para consumo do Gateway Sankhya."""

        headers = {
            "Accept": "text/xml, application/xml, application/json",
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '""',
        }
        if self.is_gateway_oauth_configured():
            headers["Authorization"] = f"Bearer {access_token}"
            headers["X-Token"] = decrypt_integration_secret(self.config.x_token)
        elif self.is_gateway_legacy_login_configured():
            headers["Authorization"] = f"Bearer {access_token}"
        elif self.is_legacy_ws_basic_configured():
            import base64

            credentials = f"{self.config.username}:{decrypt_integration_secret(self.config.password)}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        return headers

    @staticmethod
    def _resolve_expiration(data: dict[str, Any]) -> datetime:
        expires_at = data.get("expires_at") or data.get("expiresAt")
        if isinstance(expires_at, (int, float)):
            return datetime.now(timezone.utc) + timedelta(seconds=max(int(expires_at), 60))
        if isinstance(expires_at, str):
            try:
                parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                pass

        expires_in = data.get("expires_in") or data.get("expiresIn") or 3600
        try:
            ttl = int(expires_in)
        except (TypeError, ValueError):
            ttl = 3600
        return datetime.now(timezone.utc) + timedelta(seconds=max(ttl - 60, 60))
