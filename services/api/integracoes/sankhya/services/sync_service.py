"""Services para integração com ERP Sankhya."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from integracoes.models import (
    IntegrationFeature,
    IntegrationHealth,
    IntegrationJob,
    IntegrationJobTrigger,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.sankhya.models import (
    SankhyaConfig,
    SankhyaPessoa,
    SankhyaProduto,
    SankhyaSyncLog,
)
from integracoes.sankhya.schemas import SankhyaTestConnectionResponse
from integracoes.sankhya.services.canonical_adapter import SankhyaCanonicalAdapter
from integracoes.sankhya.services.auth_service import SankhyaGatewayAuthService
from integracoes.security import (
    decrypt_integration_secret,
    encrypt_integration_secret,
    mask_integration_secret,
)


class SankhyaWSClient:
    """Cliente para Web Services Sankhya BPM."""

    def __init__(self, config: SankhyaConfig):
        self.config = config
        self.auth_service = SankhyaGatewayAuthService(config)
        self.auth_model = self.auth_service.auth_model()
        self.base_url = config.api_base_url or config.ws_url or ""
        self.auth_url = config.auth_url or ""
        self._session: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._session = httpx.AsyncClient(timeout=300.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.aclose()

    def _validate_config(self) -> None:
        if self.auth_model == "GATEWAY":
            self.auth_service.validate_gateway_config()
            return
        if self.auth_model == "LEGACY":
            self.auth_service.validate_legacy_config()
            return
        raise ValueError("Configuração Sankhya incompleta: informe Gateway ou credenciais legadas")

    async def _get_auth_headers(self) -> dict[str, str]:
        self._validate_config()
        if self.auth_model == "GATEWAY":
            token = await self.auth_service.authenticate(self._session)
            return self.auth_service.build_request_headers(token)
        token_headers = self.auth_service.build_request_headers("")
        token_headers["Content-Type"] = "text/xml; charset=utf-8"
        token_headers["SOAPAction"] = '""'
        return token_headers

    async def test_connection(self) -> bool:
        if self._session is None:
            raise RuntimeError("SankhyaWSClient deve ser usado como context manager")
        try:
            soap_envelope = """<?xml version="1.0" encoding="UTF-8"?>
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                <soapenv:Header/>
                <soapenv:Body/>
            </soapenv:Envelope>"""

            response = await self._session.post(
                self.base_url,
                headers=await self._get_auth_headers(),
                content=soap_envelope,
            )
            return response.status_code == 200
        except Exception as exc:  # pragma: no cover - integração externa
            print(f"Erro ao testar conexão Sankhya: {exc}")
            return False

    async def executar_ws(
        self, service: str, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("SankhyaWSClient deve ser usado como context manager")
        soap_envelope = self._build_soap_envelope(service, method, params)

        try:
            response = await self._session.post(
                self.base_url,
                headers=await self._get_auth_headers(),
                content=soap_envelope,
            )

            if response.status_code == 200:
                return self._parse_soap_response(response.text)
            raise Exception(f"Erro WS Sankhya: {response.status_code} - {response.text}")
        except Exception as exc:  # pragma: no cover - integração externa
            raise Exception(f"Falha ao executar WS {service}.{method}: {exc}") from exc

    def _build_soap_envelope(self, service: str, method: str, params: dict[str, Any]) -> str:
        params_xml = "".join(f"<{key}>{value}</{key}>" for key, value in params.items())

        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                          xmlns:bpm="http://www.sankhya.com.br/bpm">
            <soapenv:Header/>
            <soapenv:Body>
                <bpm:{method}>
                    {params_xml}
                </bpm:{method}>
            </soapenv:Body>
        </soapenv:Envelope>"""

    def _parse_soap_response(self, response_text: str) -> dict[str, Any]:
        import re

        result = {}
        matches = re.findall(r"<([^>]+)>([^<]+)</\1>", response_text)
        for key, value in matches:
            if key not in ["soapenv", "bpm"]:
                result[key] = value
        return result


class SankhyaConfigSerializer:
    """Serializa configuração sem expor segredos."""

    @staticmethod
    def to_response(config: SankhyaConfig) -> dict[str, Any]:
        auth_service = SankhyaGatewayAuthService(config)
        return {
            "id": config.id,
            "tenant_id": config.tenant_id,
            "sankhya_environment": config.environment,
            "sankhya_api_base_url": config.api_base_url or config.ws_url,
            "sankhya_auth_url": config.auth_url,
            "sankhya_client_id": config.client_id,
            "sankhya_client_secret_configured": bool(
                decrypt_integration_secret(config.client_secret)
            ),
            "sankhya_client_secret_mask": mask_integration_secret(config.client_secret),
            "sankhya_x_token_configured": bool(decrypt_integration_secret(config.x_token)),
            "sankhya_x_token_mask": mask_integration_secret(config.x_token),
            "ws_url": config.ws_url,
            "username": config.username,
            "ativo": config.ativo,
            "ultimo_teste": config.ultimo_teste,
            "teste_status": config.teste_status,
            "ultimo_sync": config.ultimo_sync,
            "sync_interval": config.sync_interval,
            "password_configured": bool(config.password),
            "password_mask": mask_integration_secret(config.password),
            "auth_model": auth_service.auth_model(),
            "legacy_configured": auth_service.is_legacy_configured(),
            "created_at": config.created_at,
        }


class SankhyaSyncService:
    """Serviço de sincronização com Sankhya."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.adapter = SankhyaCanonicalAdapter(db)

    async def get_config(self, tenant_id: str) -> SankhyaConfig | None:
        stmt = select(SankhyaConfig).where(SankhyaConfig.tenant_id == tenant_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def _normalize_config_values(
        self,
        *,
        sankhya_environment: str | None,
        sankhya_api_base_url: str | None,
        sankhya_auth_url: str | None,
        sankhya_client_id: str | None,
        sankhya_client_secret: str | None,
        sankhya_x_token: str | None,
        ws_url: str | None,
        username: str | None,
        password: str | None,
        sync_interval: int,
        current: SankhyaConfig | None = None,
    ) -> dict[str, Any]:
        gateway_inputs = [
            sankhya_api_base_url,
            sankhya_auth_url,
            sankhya_client_id,
            sankhya_client_secret,
            sankhya_x_token,
        ]
        legacy_inputs = [ws_url, username, password]
        explicit_gateway = any(value is not None for value in gateway_inputs)
        explicit_legacy = any(value is not None for value in legacy_inputs)

        if explicit_gateway:
            auth_model = "GATEWAY"
        elif explicit_legacy:
            auth_model = "LEGACY"
        elif current is not None:
            auth_model = SankhyaGatewayAuthService(current).auth_model()
        else:
            auth_model = "GATEWAY"

        current_auth = SankhyaGatewayAuthService(current) if current else None
        current_is_gateway = current_auth.auth_model() == "GATEWAY" if current_auth else False
        current_is_legacy = current_auth.auth_model() == "LEGACY" if current_auth else False

        environment = sankhya_environment or (current.environment if current else settings.sankhya_environment)
        api_base_url = sankhya_api_base_url or (
            current.api_base_url if current and current.api_base_url else None
        )
        auth_url = sankhya_auth_url or (current.auth_url if current and current.auth_url else None)
        client_id = sankhya_client_id or (current.client_id if current and current.client_id else None)
        client_secret_raw = sankhya_client_secret
        x_token_raw = sankhya_x_token
        ws_url_value = ws_url or (current.ws_url if current and current.ws_url else None)
        username_value = username or (current.username if current and current.username else None)
        password_raw = password

        if auth_model == "INCOMPLETE":
            raise ValueError(
                "Configuração Sankhya incompleta: informe Gateway ou credenciais legadas"
            )

        if auth_model == "GATEWAY":
            if api_base_url is None:
                raise ValueError("Configuração Sankhya Gateway incompleta: sankhya_api_base_url")
            if auth_url is None:
                raise ValueError("Configuração Sankhya Gateway incompleta: sankhya_auth_url")
            if client_id is None:
                raise ValueError("Configuração Sankhya Gateway incompleta: sankhya_client_id")

            if client_secret_raw is None and current_is_gateway and current and current.client_secret:
                client_secret = current.client_secret
            elif client_secret_raw is None:
                raise ValueError("Configuração Sankhya Gateway incompleta: sankhya_client_secret")
            else:
                client_secret = encrypt_integration_secret(client_secret_raw)

            if x_token_raw is None and current_is_gateway and current and current.x_token:
                x_token = current.x_token
            elif x_token_raw is None:
                raise ValueError("Configuração Sankhya Gateway incompleta: sankhya_x_token")
            else:
                x_token = encrypt_integration_secret(x_token_raw)

            if ws_url_value is None:
                ws_url_value = api_base_url
            if username_value is None:
                username_value = client_id

            password_value = (
                encrypt_integration_secret(password_raw)
                if password_raw is not None
                else (current.password if current and current.password and current_is_legacy else None)
            )
        else:
            if ws_url_value is None:
                raise ValueError("Configuração Sankhya LEGACY incompleta: ws_url")
            if username_value is None:
                raise ValueError("Configuração Sankhya LEGACY incompleta: username")

            if password_raw is None and current_is_legacy and current and current.password:
                password_value = current.password
            elif password_raw is None:
                raise ValueError("Configuração Sankhya LEGACY incompleta: password")
            else:
                password_value = encrypt_integration_secret(password_raw)

            if api_base_url is None:
                api_base_url = ws_url_value
            if auth_url is None:
                auth_url = None
            if client_id is None:
                client_id = None
            client_secret = current.client_secret if current and current.client_secret else None
            x_token = current.x_token if current and current.x_token else None

        return {
            "environment": environment,
            "api_base_url": api_base_url,
            "auth_url": auth_url,
            "client_id": client_id,
            "client_secret": client_secret,
            "x_token": x_token,
            "ws_url": ws_url_value,
            "username": username_value,
            "password": password_value,
            "sync_interval": sync_interval,
            "auth_model": auth_model,
            "client_secret_changed": client_secret_raw is not None,
            "x_token_changed": x_token_raw is not None,
            "password_changed": password_raw is not None,
        }

    async def criar_config(
        self,
        tenant_id: str,
        *,
        sankhya_environment: str | None = None,
        sankhya_api_base_url: str | None = None,
        sankhya_auth_url: str | None = None,
        sankhya_client_id: str | None = None,
        sankhya_client_secret: str | None = None,
        sankhya_x_token: str | None = None,
        ws_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        sync_interval: int = 900,
    ) -> SankhyaConfig:
        normalized = self._normalize_config_values(
            sankhya_environment=sankhya_environment,
            sankhya_api_base_url=sankhya_api_base_url,
            sankhya_auth_url=sankhya_auth_url,
            sankhya_client_id=sankhya_client_id,
            sankhya_client_secret=sankhya_client_secret,
            sankhya_x_token=sankhya_x_token,
            ws_url=ws_url,
            username=username,
            password=password,
            sync_interval=sync_interval,
        )
        config = SankhyaConfig(
            tenant_id=tenant_id,
            environment=normalized["environment"],
            api_base_url=normalized["api_base_url"],
            auth_url=normalized["auth_url"],
            client_id=normalized["client_id"],
            client_secret=normalized["client_secret"],
            x_token=normalized["x_token"],
            ws_url=normalized["ws_url"],
            username=normalized["username"],
            password=normalized["password"],
            sync_interval=normalized["sync_interval"],
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        await self.adapter.sync_provider_config(
            config,
            password_changed=bool(normalized["client_secret"] or normalized["x_token"] or normalized["password"]),
            reason="sankhya_config_created",
        )
        return config

    async def atualizar_config(
        self,
        config: SankhyaConfig,
        *,
        sankhya_environment: str | None = None,
        sankhya_api_base_url: str | None = None,
        sankhya_auth_url: str | None = None,
        sankhya_client_id: str | None = None,
        sankhya_client_secret: str | None = None,
        sankhya_x_token: str | None = None,
        ws_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        sync_interval: int,
    ) -> SankhyaConfig:
        normalized = self._normalize_config_values(
            sankhya_environment=sankhya_environment,
            sankhya_api_base_url=sankhya_api_base_url,
            sankhya_auth_url=sankhya_auth_url,
            sankhya_client_id=sankhya_client_id,
            sankhya_client_secret=sankhya_client_secret,
            sankhya_x_token=sankhya_x_token,
            ws_url=ws_url,
            username=username,
            password=password,
            sync_interval=sync_interval,
            current=config,
        )
        password_changed = bool(
            normalized["client_secret_changed"]
            or normalized["x_token_changed"]
            or normalized["password_changed"]
        )
        config.environment = normalized["environment"]
        config.api_base_url = normalized["api_base_url"]
        config.auth_url = normalized["auth_url"]
        config.client_id = normalized["client_id"]
        if normalized["client_secret"] is not None:
            config.client_secret = normalized["client_secret"]
        if normalized["x_token"] is not None:
            config.x_token = normalized["x_token"]
        if normalized["ws_url"] is not None:
            config.ws_url = normalized["ws_url"]
        if normalized["username"] is not None:
            config.username = normalized["username"]
        if normalized["password"] is not None:
            config.password = normalized["password"]
        config.sync_interval = normalized["sync_interval"]
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        await self.adapter.sync_provider_config(
            config,
            password_changed=password_changed,
            reason="sankhya_config_updated",
        )
        return config

    async def testar_conexao(self, tenant_id: str) -> SankhyaTestConnectionResponse:
        """Executa um teste controlado do Gateway Sankhya sem persistência externa.

        Args:
            tenant_id: Identificador do tenant em escopo RLS.

        Returns:
            Resposta sanitizada do teste de conexão.
        """

        config = await self.get_config(tenant_id)
        if not config:
            return SankhyaTestConnectionResponse(
                sucesso=False,
                mensagem="Configuração não encontrada",
                token_obtido=False,
            )

        auth_service = SankhyaGatewayAuthService(config)
        diagnostic = await auth_service.test_connection()
        return SankhyaTestConnectionResponse.model_validate(diagnostic.as_dict())

    async def iniciar_sync_log(self, tenant_id: str, tipo: str, operacao: str) -> SankhyaSyncLog:
        next_id = await self._next_sync_log_id_for_sqlite()
        log = SankhyaSyncLog(
            id=next_id,
            tenant_id=tenant_id,
            tipo=tipo,
            operacao=operacao,
            status="processando",
            started_at=datetime.utcnow(),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        integration_job = await self.adapter.start_sync_job(
            tenant_id=tenant_id,
            feature_code=tipo,
            trigger_type=self._map_trigger_type(operacao),
            legacy_log_id=log.id,
            request_payload={"legacy_operacao": operacao},
        )
        log.integration_job_id = integration_job.id  # type: ignore[attr-defined]
        return log

    async def finalizar_sync_log(
        self,
        log_id: int,
        sucesso: bool,
        processados: int,
        erros: int = 0,
        erro_mensagem: str | None = None,
        tempo_ms: float = 0,
    ) -> None:
        stmt = select(SankhyaSyncLog).where(SankhyaSyncLog.id == log_id)
        log = (await self.db.execute(stmt)).scalar_one_or_none()
        if not log:
            return

        log.status = "sucesso" if sucesso else "erro"
        log.registros_processados = processados
        log.registros_erro = erros
        log.tempo_execucao_ms = tempo_ms
        log.completed_at = datetime.utcnow()
        if erro_mensagem:
            log.erro_mensagem = erro_mensagem

        config = await self.get_config(log.tenant_id)
        if config:
            config.ultimo_sync = datetime.utcnow()
            self.db.add(config)

        self.db.add(log)
        await self.db.commit()
        await self.adapter.finish_sync_job(
            tenant_id=log.tenant_id,
            feature_code=log.tipo,
            success=sucesso,
            processados=processados,
            erros=erros,
            error_message=erro_mensagem,
            tempo_ms=tempo_ms,
            trigger_type=self._map_trigger_type(log.operacao),
            legacy_log_id=log.id,
            request_payload={"legacy_operacao": log.operacao},
        )

    async def listar_logs(
        self,
        tenant_id: str,
        *,
        tipo: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[SankhyaSyncLog]:
        stmt = select(SankhyaSyncLog).where(SankhyaSyncLog.tenant_id == tenant_id)
        if tipo:
            stmt = stmt.where(SankhyaSyncLog.tipo == tipo)
        if status:
            stmt = stmt.where(SankhyaSyncLog.status == status)
        stmt = stmt.order_by(SankhyaSyncLog.created_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def obter_status_detalhado(self, tenant_id: str) -> dict[str, Any]:
        config = await self.get_config(tenant_id)
        canonical_config = await self._get_canonical_config(tenant_id)
        config_id = canonical_config.id if canonical_config else None
        health = await self._get_canonical_health(config_id)
        features = await self._list_canonical_features(config_id)
        policies = await self._list_canonical_policies(config_id)

        proximo_sync = None
        if config and config.ultimo_sync:
            proximo_sync = config.ultimo_sync + timedelta(seconds=config.sync_interval)

        legacy_status = config.teste_status if config else "nao_configurado"
        status_conexao = legacy_status or "desconhecido"
        status_canonico = canonical_config.status if canonical_config else None
        lifecycle_state = canonical_config.lifecycle_state if canonical_config else None

        if health:
            health_status = health.status
            health_origem = "canonical"
            status_origem = "canonical" if status_canonico else "legacy"
        else:
            health_status = self._map_legacy_health_status(config)
            health_origem = "legacy"
            status_origem = "legacy"

        return {
            "configurado": bool(config or canonical_config),
            "ativo": bool(config.ativo) if config else bool(canonical_config),
            "ultimo_sync": config.ultimo_sync if config else None,
            "proximo_sync": proximo_sync,
            "status_conexao": status_conexao,
            "status_legado": legacy_status,
            "status_canonico": status_canonico,
            "status_origem": status_origem,
            "health_origem": health_origem,
            "config_id_canonico": canonical_config.id if canonical_config else None,
            "lifecycle_state": lifecycle_state,
            "health_status": health_status,
            "health_summary": health.summary if health else self._legacy_health_summary(config),
            "last_success_at": (
                health.last_success_at if health else config.ultimo_sync if config else None
            ),
            "last_failure_at": health.last_failure_at if health else None,
            "consecutive_failures": health.consecutive_failures if health else 0,
            "features_habilitadas": [feature.codigo for feature in features if feature.habilitada],
            "policies_resumidas": [
                {
                    "feature_code": feature.codigo,
                    "mode": policy.mode,
                    "ativa": policy.ativa,
                    "retry_limite": policy.retry_limite,
                    "trigger_expression": policy.trigger_expression,
                }
                for policy, feature in policies
            ],
        }

    async def obter_health_detalhado(self, tenant_id: str) -> dict[str, Any]:
        config = await self.get_config(tenant_id)
        canonical_config = await self._get_canonical_config(tenant_id)
        health = await self._get_canonical_health(canonical_config.id if canonical_config else None)

        if health:
            details = self._mask_sensitive_payload(health.details_payload)
            return {
                "configurado": True,
                "origem": "canonical",
                "status": health.status,
                "summary": health.summary,
                "checked_at": health.checked_at,
                "last_success_at": health.last_success_at,
                "last_failure_at": health.last_failure_at,
                "consecutive_failures": health.consecutive_failures,
                "details": details,
            }

        return {
            "configurado": bool(config),
            "origem": "legacy",
            "status": self._map_legacy_health_status(config),
            "summary": self._legacy_health_summary(config),
            "checked_at": config.ultimo_teste if config else None,
            "last_success_at": (
                config.ultimo_sync if config and config.teste_status == "sucesso" else None
            ),
            "last_failure_at": (
                config.ultimo_teste if config and config.teste_status == "erro" else None
            ),
            "consecutive_failures": 0,
            "details": None,
        }

    async def listar_jobs(
        self,
        tenant_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        canonical_config = await self._get_canonical_config(tenant_id)
        if not canonical_config:
            return []

        features = await self._list_canonical_features(canonical_config.id)
        feature_by_id = {feature.id: feature for feature in features}

        stmt = (
            select(IntegrationJob)
            .where(
                IntegrationJob.tenant_id == tenant_id,
                IntegrationJob.config_id == canonical_config.id,
            )
            .order_by(IntegrationJob.created_at.desc())
            .limit(limit)
        )
        jobs = list((await self.db.execute(stmt)).scalars().all())

        return [
            self._serialize_job(job, feature_by_id.get(job.feature_id))
            for job in jobs
        ]

    async def listar_logs_enriquecidos(
        self,
        tenant_id: str,
        *,
        tipo: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        logs = await self.listar_logs(tenant_id, tipo=tipo, status=status, limit=limit)
        jobs = await self.listar_jobs(tenant_id, limit=limit * 2)
        jobs_by_legacy_log_id = {
            job["legacy_log_id"]: job for job in jobs if job.get("legacy_log_id") is not None
        }

        enriched_logs: list[dict[str, Any]] = []
        for log in logs:
            job = jobs_by_legacy_log_id.get(log.id)
            enriched_logs.append(
                {
                    "id": log.id,
                    "tenant_id": log.tenant_id,
                    "tipo": log.tipo,
                    "operacao": log.operacao,
                    "status": log.status,
                    "registros_processados": log.registros_processados,
                    "registros_sucesso": log.registros_sucesso,
                    "registros_erro": log.registros_erro,
                    "tempo_execucao_ms": log.tempo_execucao_ms,
                    "created_at": log.created_at,
                    "started_at": log.started_at,
                    "completed_at": log.completed_at,
                    "origem_dados": "canonical+legacy" if job else "legacy",
                    "integration_job_id": job["id"] if job else None,
                    "feature_code": job["feature_code"] if job else None,
                    "job_status": job["job_status"] if job else None,
                    "trigger_type": job["trigger_type"] if job else None,
                    "job_started_at": job["started_at"] if job else None,
                    "job_finished_at": job["finished_at"] if job else None,
                    "result_payload": job["result_payload"] if job else None,
                    "error_payload": job["error_payload"] if job else log.erro_mensagem,
                }
            )
        return enriched_logs

    async def listar_timeline_operacional(
        self,
        tenant_id: str,
        *,
        limit: int = 50,
        status: str | None = None,
        feature_code: str | None = None,
        origem: str | None = None,
    ) -> list[dict[str, Any]]:
        logs = await self.listar_logs_enriquecidos(tenant_id, limit=limit)
        jobs = await self.listar_jobs(tenant_id, limit=limit)
        health = await self.obter_health_detalhado(tenant_id)

        timeline = [
            *self._build_job_timeline_entries(jobs),
            *self._build_log_timeline_entries(logs),
            self._build_health_timeline_entry(health),
        ]
        filtered = self._filter_timeline_entries(
            timeline,
            status=status,
            feature_code=feature_code,
            origem=origem,
        )
        filtered.sort(key=lambda item: item["occurred_at"], reverse=True)
        return filtered[:limit]

    async def obter_diagnostico_operacional(self, tenant_id: str) -> dict[str, Any]:
        status_payload = await self.obter_status_detalhado(tenant_id)
        health_payload = await self.obter_health_detalhado(tenant_id)
        jobs = await self.listar_jobs(tenant_id, limit=50)
        logs = await self.listar_logs_enriquecidos(tenant_id, limit=50)

        ultimo_sucesso_at = self._resolve_latest_timestamp(
            [status_payload.get("last_success_at")]
            + [job.get("finished_at") for job in jobs if job["job_status"] == "SUCCESS"]
            + [log.get("completed_at") for log in logs if log["status"] == "sucesso"]
        )
        ultima_falha_at = self._resolve_latest_timestamp(
            [status_payload.get("last_failure_at")]
            + [job.get("finished_at") for job in jobs if job["job_status"] == "FAILED"]
            + [log.get("completed_at") for log in logs if log["status"] == "erro"]
        )
        falhas_consecutivas = int(
            health_payload.get("consecutive_failures")
            or status_payload.get("consecutive_failures")
            or 0
        )
        jobs_pendentes = sum(
            1 for job in jobs if job["job_status"] in {"PENDING", "RUNNING", "RETRYING"}
        )
        jobs_falhos = sum(1 for job in jobs if job["job_status"] == "FAILED")

        feature_mais_problematica = self._resolve_problematic_feature(jobs, logs)
        health_atual = str(
            health_payload.get("status")
            or status_payload.get("health_status")
            or "DISCONNECTED"
        )
        status_degradacao = (
            "degradado"
            if health_atual in {"DEGRADED", "PARTIAL_FAILURE", "AUTH_ERROR", "CONFIG_ERROR"}
            else "estavel"
        )

        return {
            "origem": (
                health_payload.get("origem")
                or status_payload.get("health_origem")
                or "legacy"
            ),
            "health_atual": health_atual,
            "status_degradacao": status_degradacao,
            "ultimo_sucesso_at": ultimo_sucesso_at,
            "ultima_falha_at": ultima_falha_at,
            "falhas_consecutivas": falhas_consecutivas,
            "feature_mais_problematica": feature_mais_problematica,
            "jobs_pendentes": jobs_pendentes,
            "jobs_falhos": jobs_falhos,
            "recomendacao_operacional": self._build_operational_recommendation(
                health_atual=health_atual,
                falhas_consecutivas=falhas_consecutivas,
                jobs_pendentes=jobs_pendentes,
                feature_mais_problematica=feature_mais_problematica,
            ),
        }

    @staticmethod
    def _map_trigger_type(operacao: str) -> IntegrationJobTrigger:
        if operacao == "sync":
            return IntegrationJobTrigger.SCHEDULED
        return IntegrationJobTrigger.MANUAL

    async def _next_sync_log_id_for_sqlite(self) -> int | None:
        bind = self.db.get_bind()
        dialect = getattr(bind, "dialect", None)
        if getattr(dialect, "name", "") != "sqlite":
            return None

        stmt = select(func.coalesce(func.max(SankhyaSyncLog.id), 0) + 1)
        return int((await self.db.execute(stmt)).scalar_one())

    async def _get_canonical_config(self, tenant_id: str) -> TenantIntegracao | None:
        stmt = (
            select(TenantIntegracao)
            .join(MarketplaceIntegracao, TenantIntegracao.integracao_id == MarketplaceIntegracao.id)
            .where(
                TenantIntegracao.tenant_id == tenant_id,
                MarketplaceIntegracao.slug == "sankhya",
                TenantIntegracao.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _get_canonical_health(self, config_id: int | None) -> IntegrationHealth | None:
        if config_id is None:
            return None
        stmt = select(IntegrationHealth).where(IntegrationHealth.config_id == config_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _list_canonical_features(self, config_id: int | None) -> list[IntegrationFeature]:
        if config_id is None:
            return []
        stmt = (
            select(IntegrationFeature)
            .where(
                IntegrationFeature.config_id == config_id,
                IntegrationFeature.deleted_at.is_(None),
            )
            .order_by(IntegrationFeature.codigo.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def _list_canonical_policies(
        self,
        config_id: int | None,
    ) -> list[tuple[IntegrationSyncPolicy, IntegrationFeature]]:
        if config_id is None:
            return []
        stmt = (
            select(IntegrationSyncPolicy, IntegrationFeature)
            .join(IntegrationFeature, IntegrationSyncPolicy.feature_id == IntegrationFeature.id)
            .where(
                IntegrationSyncPolicy.config_id == config_id,
                IntegrationSyncPolicy.deleted_at.is_(None),
                IntegrationFeature.deleted_at.is_(None),
            )
            .order_by(IntegrationFeature.codigo.asc())
        )
        return list((await self.db.execute(stmt)).all())

    @staticmethod
    def _map_legacy_health_status(config: SankhyaConfig | None) -> str:
        if not config:
            return "DISCONNECTED"
        if config.teste_status == "sucesso":
            return "CONNECTED"
        if config.teste_status == "erro":
            return "DISCONNECTED"
        return "CONFIG_ERROR"

    @staticmethod
    def _legacy_health_summary(config: SankhyaConfig | None) -> str:
        if not config:
            return "Integração Sankhya ainda não configurada."
        if config.teste_status == "sucesso":
            return "Último teste de conexão executado com sucesso."
        if config.teste_status == "erro":
            return "Último teste de conexão falhou."
        return "Configuração existente sem health canônico disponível."

    def _serialize_job(
        self,
        job: IntegrationJob,
        feature: IntegrationFeature | None,
    ) -> dict[str, Any]:
        legacy_log_id = self._extract_legacy_log_id(job)
        error_payload = job.error_message
        if job.status == "FAILED" and job.result_payload:
            error_payload = job.result_payload

        return {
            "id": str(job.id),
            "tenant_id": job.tenant_id,
            "config_id": job.config_id,
            "feature_code": feature.codigo if feature else None,
            "job_status": job.status,
            "trigger_type": job.trigger_type,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "processados": job.processados,
            "sucessos": job.sucessos,
            "erros": job.erros,
            "correlation_id": str(job.correlation_id) if job.correlation_id else None,
            "legacy_log_id": legacy_log_id,
            "result_payload": self._mask_sensitive_payload(job.result_payload),
            "error_payload": self._mask_sensitive_payload(error_payload),
        }

    @staticmethod
    def _extract_legacy_log_id(job: IntegrationJob) -> int | None:
        payload = job.request_payload or {}
        legacy_log_id = payload.get("legacy_log_id")
        if isinstance(legacy_log_id, int):
            return legacy_log_id

        return None

    def _mask_sensitive_payload(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            masked: dict[str, Any] = {}
            for key, value in payload.items():
                lowered = key.lower()
                if any(
                    token in lowered
                    for token in (
                        "password",
                        "token",
                        "secret",
                        "private_key",
                        "certificate",
                    )
                ):
                    masked[key] = "••••••••"
                else:
                    masked[key] = self._mask_sensitive_payload(value)
            return masked
        if isinstance(payload, list):
            return [self._mask_sensitive_payload(item) for item in payload]
        return payload

    def _build_job_timeline_entries(
        self,
        jobs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for job in jobs:
            status = job["job_status"]
            event_type = self._map_job_event_type(status)
            started_at = job.get("started_at")
            finished_at = job.get("finished_at")
            occurred_at = finished_at or started_at or datetime.utcnow()
            entries.append(
                {
                    "id": f"job:{job['id']}",
                    "tipo_registro": "canonical_job",
                    "origem_dado": "canonical",
                    "feature_code": job.get("feature_code"),
                    "status": status,
                    "event_type": event_type,
                    "resumo": self._build_job_summary(job),
                    "occurred_at": occurred_at,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duracao_ms": self._duration_ms(started_at, finished_at),
                    "processados": job.get("processados", 0),
                    "sucessos": job.get("sucessos", 0),
                    "erros": job.get("erros", 0),
                    "correlation_id": job.get("correlation_id"),
                    "payload": job.get("error_payload") or job.get("result_payload"),
                }
            )
        return entries

    def _build_log_timeline_entries(
        self,
        logs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for log in logs:
            started_at = log.get("job_started_at") or log.get("started_at")
            finished_at = log.get("job_finished_at") or log.get("completed_at")
            occurred_at = finished_at or started_at or log["created_at"]
            entries.append(
                {
                    "id": f"log:{log['id']}",
                    "tipo_registro": "legacy_log",
                    "origem_dado": log.get("origem_dados", "legacy"),
                    "feature_code": log.get("feature_code") or log.get("tipo"),
                    "status": log.get("job_status") or log["status"],
                    "event_type": self._map_log_event_type(log),
                    "resumo": self._build_log_summary(log),
                    "occurred_at": occurred_at,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duracao_ms": self._resolve_log_duration_ms(log),
                    "processados": log.get("registros_processados", 0),
                    "sucessos": log.get("registros_sucesso", 0),
                    "erros": log.get("registros_erro", 0),
                    "correlation_id": log.get("integration_job_id"),
                    "payload": log.get("error_payload") or log.get("result_payload"),
                }
            )
        return entries

    def _build_health_timeline_entry(self, health: dict[str, Any]) -> dict[str, Any]:
        occurred_at = health.get("checked_at") or datetime.utcnow()
        return {
            "id": "health:current",
            "tipo_registro": "health_snapshot",
            "origem_dado": health.get("origem", "legacy"),
            "feature_code": None,
            "status": health.get("status", "DISCONNECTED"),
            "event_type": "integrations.health_snapshot",
            "resumo": health.get("summary") or "Snapshot atual de health da integração.",
            "occurred_at": occurred_at,
            "started_at": None,
            "finished_at": occurred_at,
            "duracao_ms": None,
            "processados": 0,
            "sucessos": 0,
            "erros": health.get("consecutive_failures", 0),
            "correlation_id": None,
            "payload": health.get("details"),
        }

    def _filter_timeline_entries(
        self,
        entries: list[dict[str, Any]],
        *,
        status: str | None,
        feature_code: str | None,
        origem: str | None,
    ) -> list[dict[str, Any]]:
        filtered = entries
        if status:
            normalized_status = status.lower()
            filtered = [
                item for item in filtered if str(item["status"]).lower() == normalized_status
            ]
        if feature_code:
            normalized_feature = feature_code.lower()
            filtered = [
                item
                for item in filtered
                if str(item.get("feature_code") or "").lower() == normalized_feature
            ]
        if origem:
            normalized_origin = origem.lower()
            filtered = [
                item
                for item in filtered
                if str(item.get("origem_dado") or "").lower() == normalized_origin
            ]
        return filtered

    @staticmethod
    def _resolve_latest_timestamp(candidates: list[Any]) -> datetime | None:
        valid = [candidate for candidate in candidates if isinstance(candidate, datetime)]
        return max(valid) if valid else None

    @staticmethod
    def _resolve_problematic_feature(
        jobs: list[dict[str, Any]],
        logs: list[dict[str, Any]],
    ) -> str | None:
        scores: dict[str, int] = {}
        for job in jobs:
            if job["job_status"] == "FAILED" and job.get("feature_code"):
                feature_code = str(job["feature_code"])
                scores[feature_code] = scores.get(feature_code, 0) + 1
        for log in logs:
            log_failed = (log.get("job_status") == "FAILED") or (log["status"] == "erro")
            if log_failed:
                feature_code = str(log.get("feature_code") or log.get("tipo") or "")
                if feature_code:
                    scores[feature_code] = scores.get(feature_code, 0) + 1
        if not scores:
            return None
        return max(scores.items(), key=lambda item: item[1])[0]

    @staticmethod
    def _build_operational_recommendation(
        *,
        health_atual: str,
        falhas_consecutivas: int,
        jobs_pendentes: int,
        feature_mais_problematica: str | None,
    ) -> str:
        if health_atual in {"AUTH_ERROR", "CONFIG_ERROR"}:
            return "Revisar credenciais e parâmetros técnicos antes de executar novo sync."
        if falhas_consecutivas >= 3 and feature_mais_problematica:
            return (
                "Priorizar troubleshooting da feature "
                f"{feature_mais_problematica} antes de novas execuções manuais."
            )
        if jobs_pendentes > 0:
            return "Aguardar o processamento dos jobs em andamento antes de disparar novos syncs."
        if health_atual in {"DEGRADED", "PARTIAL_FAILURE"}:
            return "Monitorar os próximos jobs e validar os erros recentes do provider."
        return "Integração operando de forma estável no momento."

    @staticmethod
    def _map_job_event_type(status: str) -> str:
        if status == "RUNNING":
            return "integrations.sync_started"
        if status == "SUCCESS":
            return "integrations.sync_completed"
        if status == "FAILED":
            return "integrations.sync_failed"
        return "integrations.sync_updated"

    def _build_job_summary(self, job: dict[str, Any]) -> str:
        feature_code = job.get("feature_code") or "feature_indefinida"
        return (
            f"Job canônico {job['job_status']} para {feature_code}: "
            f"{job.get('sucessos', 0)}/{job.get('processados', 0)} com sucesso."
        )

    def _build_log_summary(self, log: dict[str, Any]) -> str:
        feature_code = log.get("feature_code") or log.get("tipo") or "feature_indefinida"
        return (
            f"Log legado {log.get('job_status') or log['status']} para {feature_code}: "
            f"{log.get('registros_sucesso', 0)}/{log.get('registros_processados', 0)} com sucesso."
        )

    @staticmethod
    def _map_log_event_type(log: dict[str, Any]) -> str:
        log_status = log.get("job_status") or log["status"]
        if log_status in {"RUNNING", "processando"}:
            return "integrations.sync_started"
        if log_status in {"SUCCESS", "sucesso"}:
            return "integrations.sync_completed"
        if log_status in {"FAILED", "erro"}:
            return "integrations.sync_failed"
        return "integrations.sync_updated"

    @staticmethod
    def _duration_ms(started_at: datetime | None, finished_at: datetime | None) -> float | None:
        if not started_at or not finished_at:
            return None
        return (finished_at - started_at).total_seconds() * 1000

    def _resolve_log_duration_ms(self, log: dict[str, Any]) -> float | None:
        if log.get("tempo_execucao_ms") is not None:
            return float(log["tempo_execucao_ms"])
        started_at = log.get("job_started_at") or log.get("started_at")
        finished_at = log.get("job_finished_at") or log.get("completed_at")
        if isinstance(started_at, datetime) and isinstance(finished_at, datetime):
            return self._duration_ms(started_at, finished_at)
        return None


class SankhyaPessoaService:
    """Serviço para sincronização de pessoas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def importar_pessoas(self, tenant_id: str, log_id: int | None = None) -> int:
        config = await self._get_config(tenant_id)
        if not config:
            return 0

        importados = 0

        async with SankhyaWSClient(config) as client:
            try:
                resultado = await client.executar_ws("PessoaFisica", "findAll", {})
                for pessoa_data in resultado.get("pessoas", []):
                    await self._salvar_pessoa_fisica(tenant_id, pessoa_data)
                    importados += 1
            except Exception as exc:  # pragma: no cover - integração externa
                print(f"Erro ao importar pessoas físicas: {exc}")

            try:
                resultado = await client.executar_ws("PessoaJuridica", "findAll", {})
                for pessoa_data in resultado.get("pessoas", []):
                    await self._salvar_pessoa_juridica(tenant_id, pessoa_data)
                    importados += 1
            except Exception as exc:  # pragma: no cover - integração externa
                print(f"Erro ao importar pessoas jurídicas: {exc}")

        if log_id:
            await self._finalizar_log(log_id, True, importados)

        return importados

    async def listar_pessoas(
        self,
        tenant_id: str,
        *,
        tipo: str | None = None,
        ativo: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SankhyaPessoa]:
        stmt = select(SankhyaPessoa).where(SankhyaPessoa.tenant_id == tenant_id)
        if tipo:
            stmt = stmt.where(SankhyaPessoa.tipo == tipo)
        if ativo is not None:
            stmt = stmt.where(SankhyaPessoa.ativo == ativo)
        stmt = stmt.offset(skip).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def _salvar_pessoa_fisica(self, tenant_id: str, data: dict[str, Any]) -> SankhyaPessoa:
        pessoa = SankhyaPessoa(
            tenant_id=tenant_id,
            sankhya_id=str(data.get("CODPARC", "")),
            tipo="FISICA",
            nome=data.get("NOME", ""),
            cpf=data.get("CGC_CPF", ""),
            email=data.get("EMAIL", ""),
            telefone=data.get("TELEFONE", ""),
            endereco=data.get("ENDERECO", ""),
            bairro=data.get("BAIRRO", ""),
            cidade=data.get("CIDADE", ""),
            uf=data.get("UF", ""),
            cep=data.get("CEP", ""),
            ativo=data.get("ATIVO", "S") == "S",
            sincronizado_em=datetime.utcnow(),
        )

        stmt = select(SankhyaPessoa).where(SankhyaPessoa.sankhya_id == pessoa.sankhya_id)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()

        if existing:
            for key, value in pessoa.__dict__.items():
                if not key.startswith("_"):
                    setattr(existing, key, value)
            pessoa = existing
        else:
            self.db.add(pessoa)

        await self.db.commit()
        await self.db.refresh(pessoa)
        return pessoa

    async def _salvar_pessoa_juridica(self, tenant_id: str, data: dict[str, Any]) -> SankhyaPessoa:
        pessoa = SankhyaPessoa(
            tenant_id=tenant_id,
            sankhya_id=str(data.get("CODPARC", "")),
            tipo="JURIDICA",
            nome=data.get("NOME", ""),
            nome_fantasia=data.get("NOMEFANTASIA", ""),
            cnpj=data.get("CGC_CPF", ""),
            ie=data.get("INSCRICAO", ""),
            email=data.get("EMAIL", ""),
            telefone=data.get("TELEFONE", ""),
            endereco=data.get("ENDERECO", ""),
            bairro=data.get("BAIRRO", ""),
            cidade=data.get("CIDADE", ""),
            uf=data.get("UF", ""),
            cep=data.get("CEP", ""),
            ativo=data.get("ATIVO", "S") == "S",
            sincronizado_em=datetime.utcnow(),
        )

        stmt = select(SankhyaPessoa).where(SankhyaPessoa.sankhya_id == pessoa.sankhya_id)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()

        if existing:
            for key, value in pessoa.__dict__.items():
                if not key.startswith("_"):
                    setattr(existing, key, value)
            pessoa = existing
        else:
            self.db.add(pessoa)

        await self.db.commit()
        await self.db.refresh(pessoa)
        return pessoa

    async def _get_config(self, tenant_id: str) -> SankhyaConfig | None:
        stmt = select(SankhyaConfig).where(SankhyaConfig.tenant_id == tenant_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _finalizar_log(self, log_id: int, sucesso: bool, processados: int) -> None:
        service = SankhyaSyncService(self.db)
        await service.finalizar_sync_log(log_id, sucesso, processados)


class SankhyaProdutoService:
    """Serviço para sincronização de produtos."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def importar_produtos(self, tenant_id: str, log_id: int | None = None) -> int:
        config = await self._get_config(tenant_id)
        if not config:
            return 0

        importados = 0

        async with SankhyaWSClient(config) as client:
            try:
                resultado = await client.executar_ws("Produto", "findAll", {})
                for produto_data in resultado.get("produtos", []):
                    await self._salvar_produto(tenant_id, produto_data)
                    importados += 1
            except Exception as exc:  # pragma: no cover - integração externa
                print(f"Erro ao importar produtos: {exc}")

        if log_id:
            await self._finalizar_log(log_id, True, importados)

        return importados

    async def listar_produtos(
        self,
        tenant_id: str,
        *,
        ativo: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SankhyaProduto]:
        stmt = select(SankhyaProduto).where(SankhyaProduto.tenant_id == tenant_id)
        if ativo is not None:
            stmt = stmt.where(SankhyaProduto.ativo == ativo)
        stmt = stmt.offset(skip).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def _salvar_produto(self, tenant_id: str, data: dict[str, Any]) -> SankhyaProduto:
        produto = SankhyaProduto(
            tenant_id=tenant_id,
            sankhya_id=str(data.get("CODPROD", "")),
            codigo=data.get("CODPROD", ""),
            nome=data.get("DESCRPROD", ""),
            descricao=data.get("COMPLEMENTO", ""),
            ncm=data.get("NCM", ""),
            unidade=data.get("UNIDADE", "UN"),
            preco_custo=float(data.get("VLCUSTO", 0) or 0),
            preco_venda=float(data.get("VLVENDA", 0) or 0),
            ativo=data.get("ATIVO", "S") == "S",
            sincronizado_em=datetime.utcnow(),
        )

        stmt = select(SankhyaProduto).where(SankhyaProduto.sankhya_id == produto.sankhya_id)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()

        if existing:
            for key, value in produto.__dict__.items():
                if not key.startswith("_"):
                    setattr(existing, key, value)
            produto = existing
        else:
            self.db.add(produto)

        await self.db.commit()
        await self.db.refresh(produto)
        return produto

    async def _get_config(self, tenant_id: str) -> SankhyaConfig | None:
        stmt = select(SankhyaConfig).where(SankhyaConfig.tenant_id == tenant_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _finalizar_log(self, log_id: int, sucesso: bool, processados: int) -> None:
        service = SankhyaSyncService(self.db)
        await service.finalizar_sync_log(log_id, sucesso, processados)
