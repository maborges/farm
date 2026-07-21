# ruff: noqa: S105, S106
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Column, Table, func, select
from sqlalchemy import Uuid as UUIDType
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import Base
from integracoes.erp.policy_service import ErpSyncPolicyService
from integracoes.models import (
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationJob,
    IntegrationJobStatus,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncPolicy,
    IntegrationVersion,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.sankhya.models import SankhyaConfig, SankhyaSyncLog
from integracoes.sankhya.services.canonical_adapter import (
    SankhyaCanonicalAdapter,
    _connection_schema_payload,
    _credential_schema_payload,
    _is_unique_conflict_for_constraints,
)
from integracoes.sankhya.services.nfe_financeiro_service import SankhyaNFeService
from integracoes.sankhya.services.sync_service import (
    SankhyaSyncService,
    _is_sankhya_config_unique_conflict,
)
from integracoes.security import decrypt_integration_secret, encrypt_integration_secret
from tests.unit.integracoes.conftest import criar_tenant_real

REPO_ROOT = Path(__file__).resolve().parents[5]
ROUTERS_FILE = REPO_ROOT / "services/api/integracoes/sankhya/routers/__init__.py"

if "domain_event_outbox" not in Base.metadata.tables:
    Table(
        "domain_event_outbox",
        Base.metadata,
        Column("id", UUIDType(as_uuid=True), primary_key=True),
    )


async def _next_sankhya_config_id(session: AsyncSession) -> int:
    # sankhya_config.id não possui sequence/default no banco (débito já
    # registrado); replica o contorno usado em produção por
    # SankhyaSyncService (max(id) + 1), sem alterar model ou migration.
    return (await session.scalar(select(func.coalesce(func.max(SankhyaConfig.id), 0) + 1))) or 1


async def _legacy_sankhya_config(
    session: AsyncSession, tenant_id: str | None = None
) -> SankhyaConfig:
    tenant_id = tenant_id or await criar_tenant_real(session)
    service = SankhyaSyncService(session)
    return await service.criar_config(
        tenant_id=tenant_id,
        ws_url="https://erp.example/ws",
        username="usuario",
        password="segredo",
        sync_interval=900,
    )


async def _gateway_sankhya_config(
    session: AsyncSession, tenant_id: str | None = None
) -> SankhyaConfig:
    tenant_id = tenant_id or await criar_tenant_real(session)
    service = SankhyaSyncService(session)
    return await service.criar_config(
        tenant_id=tenant_id,
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/authenticate",
        sankhya_client_id="client-123",
        sankhya_client_secret="client-secret",
        sankhya_x_token="x-token",
        sync_interval=900,
    )


@pytest.mark.asyncio
async def test_adapter_cria_config_canonica_features_policies_e_health(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[Any] = []

    async def fake_publish(event: Any, **_: Any) -> None:
        events.append(event)

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    legacy = await _legacy_sankhya_config(session)

    config = (
        await session.execute(
            select(TenantIntegracao).where(
                TenantIntegracao.tenant_id == legacy.tenant_id,
            )
        )
    ).scalar_one()
    provider = (
        await session.execute(
            select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == "sankhya")
        )
    ).scalar_one()
    features = list(
        (
            await session.execute(
                select(IntegrationFeature).where(IntegrationFeature.config_id == config.id)
            )
        ).scalars()
    )
    policies = list(
        (
            await session.execute(
                select(IntegrationSyncPolicy).where(IntegrationSyncPolicy.config_id == config.id)
            )
        ).scalars()
    )
    health = (
        await session.execute(
            select(IntegrationHealth).where(IntegrationHealth.config_id == config.id)
        )
    ).scalar_one()

    assert config.scope_type == IntegrationScope.TENANT.value
    assert config.connection_payload["ws_url"] == "https://erp.example/ws"
    assert {feature.codigo for feature in features} == {
        "pessoas",
        "produtos",
        "financeiro",
        "nfe",
        "pedidos",
        "estoque",
    }
    assert len(policies) == 6
    assert health.status in {
        IntegrationHealthStatus.CONNECTED.value,
        IntegrationHealthStatus.DISCONNECTED.value,
    }
    assert provider.provider_definition["provider_code"] == "sankhya"
    assert provider.provider_definition["supported_scopes"] == [
        IntegrationScope.TENANT.value,
        IntegrationScope.ESTABELECIMENTO.value,
    ]
    assert (
        "erp.cadastros.pessoas.importar" in provider.provider_definition["supported_capabilities"]
    )
    assert provider.feature_schema["supported_features"] == [
        "pessoas",
        "produtos",
        "financeiro",
        "nfe",
        "pedidos",
        "estoque",
    ]
    pessoas_capability = next(
        item
        for item in provider.feature_schema["capability_matrix"]
        if item["feature_code"] == "pessoas"
    )
    assert pessoas_capability["status"] == "SUPPORTED"
    assert pessoas_capability["maturity"] == "TESTED"
    assert (
        provider.sync_schema["retry"]["max_attempts_source"] == "IntegrationSyncPolicy.max_retries"
    )
    assert provider.sync_schema["polling"]["default_features"] == ["financeiro", "nfe"]
    assert provider.health_schema["diagnostics"]["connection_test"] is True
    pessoas_feature = next(feature for feature in features if feature.codigo == "pessoas")
    assert pessoas_feature.settings_payload["capability_code"] == "erp.cadastros.pessoas.importar"
    assert pessoas_feature.settings_payload["pilot_tier"] == "P0"
    financeiro_policy = next(policy for policy in policies if policy.feature.codigo == "financeiro")
    assert financeiro_policy.settings_payload["default_canonical_mode"] == "POLLING"
    assert financeiro_policy.settings_payload["retry_managed_by"] == "IntegrationSyncPolicy"
    assert any(event.event_type == "integrations.configured" for event in events)


@pytest.mark.asyncio
async def test_politica_publica_endpoint_resolvido_por_cadastro(
    session: AsyncSession,
) -> None:
    config = await _gateway_sankhya_config(session)

    policies = await ErpSyncPolicyService(session).listar(uuid.UUID(config.tenant_id))

    pessoas = next(policy for policy in policies if policy.feature_code == "pessoas")
    assert pessoas.endpoint_service == "CRUDServiceProvider.loadRecords"
    assert pessoas.endpoint_entity == "Parceiro"
    assert pessoas.endpoint_url == (
        "https://gateway.example/api/gateway/v1/mge/service.sbr"
        "?serviceName=CRUDServiceProvider.loadRecords&outputType=json"
    )


@pytest.mark.asyncio
async def test_adapter_preserva_politica_personalizada_ao_atualizar_config(
    session: AsyncSession,
) -> None:
    legacy = await _legacy_sankhya_config(session)
    policy = (
        await session.execute(
            select(IntegrationSyncPolicy)
            .join(IntegrationFeature, IntegrationSyncPolicy.feature_id == IntegrationFeature.id)
            .where(
                IntegrationSyncPolicy.tenant_id == legacy.tenant_id,
                IntegrationFeature.codigo == "produtos",
            )
        )
    ).scalar_one()
    policy.mode = "AGENDADO"
    policy.trigger_expression = "0 * * * *"
    policy.retry_limite = 5
    policy.ativa = False
    await session.commit()

    await SankhyaCanonicalAdapter(session).sync_provider_config(
        legacy,
        password_changed=False,
        reason="config_updated",
    )
    await session.refresh(policy)

    assert policy.mode == "AGENDADO"
    assert policy.trigger_expression == "0 * * * *"
    assert policy.retry_limite == 5
    assert policy.ativa is False


@pytest.mark.asyncio
async def test_adapter_gateway_bundles_segredos_e_conexao_canonica(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    gateway = await _gateway_sankhya_config(session)

    config = (
        await session.execute(
            select(TenantIntegracao).where(
                TenantIntegracao.tenant_id == gateway.tenant_id,
            )
        )
    ).scalar_one()
    credential = (
        await session.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.tenant_id == gateway.tenant_id,
            )
        )
    ).scalar_one()

    credential_payload = json.loads(decrypt_integration_secret(credential.segredo_criptografado))

    assert config.connection_payload["sankhya_api_base_url"] == "https://gateway.example/api"
    assert config.connection_payload["auth_model"] == "gateway_oauth_client_credentials"
    assert config.credenciais["auth_model"] == "gateway_oauth_client_credentials"
    assert credential_payload["sankhya_client_secret"] == "client-secret"
    assert credential_payload["sankhya_x_token"] == "x-token"


@pytest.mark.asyncio
async def test_adapter_publica_schema_editavel_no_provider(session: AsyncSession) -> None:
    await _legacy_sankhya_config(session)

    provider = (
        await session.execute(
            select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == "sankhya")
        )
    ).scalar_one()

    connection_fields = {field["key"] for field in provider.connection_schema["fields"]}
    credential_fields = {field["key"] for field in provider.credential_schema["fields"]}

    assert connection_fields == {
        "sankhya_environment",
        "sankhya_api_base_url",
        "sankhya_auth_url",
        "auth_model",
        "ws_url",
        "sync_interval",
    }
    assert credential_fields == {
        "sankhya_client_id",
        "sankhya_client_secret",
        "sankhya_x_token",
        "sankhya_token",
        "sankhya_appkey",
        "username",
        "password",
    }
    assert "ultimo_teste" not in connection_fields
    assert "teste_status" not in connection_fields
    assert "ultimo_sync" not in connection_fields
    assert "legacy_auth_model" not in credential_fields

    environment_field = next(
        field
        for field in provider.connection_schema["fields"]
        if field["key"] == "sankhya_environment"
    )
    assert environment_field["default"] == "producao"
    assert [option["value"] for option in environment_field["options"]] == [
        "producao",
        "homologacao",
        "sandbox",
    ]

    auth_model_field = next(
        field for field in provider.connection_schema["fields"] if field["key"] == "auth_model"
    )
    assert [option["value"] for option in auth_model_field["options"]] == [
        "gateway_oauth_client_credentials",
        "gateway_legacy_login",
        "legacy_ws_basic_auth",
    ]


@pytest.mark.asyncio
async def test_adapter_atualiza_schema_de_provider_existente(session: AsyncSession) -> None:
    provider = (
        await session.execute(
            select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == "sankhya")
        )
    ).scalar_one_or_none()
    stub_schema = {"schema_version": 1, "required": [], "optional": [], "fields": []}
    if provider is None:
        provider = MarketplaceIntegracao(
            nome="Sankhya",
            slug="sankhya",
            provider_type="ERP",
            categoria="ERP",
            ativa=True,
            oficial=True,
            connection_schema=stub_schema,
            credential_schema=stub_schema,
            provider_definition={"provider_code": "sankhya"},
            feature_schema={"capability_matrix": []},
            sync_schema={},
            health_schema={},
        )
    else:
        provider.connection_schema = stub_schema
        provider.credential_schema = stub_schema
    session.add(provider)
    await session.commit()

    await _legacy_sankhya_config(session)
    await session.refresh(provider)

    assert provider.connection_schema == _connection_schema_payload()
    assert provider.credential_schema == _credential_schema_payload()


@pytest.mark.asyncio
async def test_adapter_rotaciona_credencial_e_versiona_snapshot(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[Any] = []

    async def fake_publish(event: Any, **_: Any) -> None:
        events.append(event)

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    legacy = await _legacy_sankhya_config(session)
    service = SankhyaSyncService(session)
    await service.atualizar_config(
        legacy,
        ws_url="https://erp.example/ws/v2",
        username="usuario-2",
        password="segredo-2",
        sync_interval=1200,
    )

    credentials = list(
        (
            await session.execute(
                select(IntegrationCredential)
                .where(IntegrationCredential.tenant_id == legacy.tenant_id)
                .order_by(IntegrationCredential.version_number.asc())
            )
        ).scalars()
    )
    versions = list(
        (
            await session.execute(
                select(IntegrationVersion).order_by(IntegrationVersion.version_number.asc())
            )
        ).scalars()
    )

    assert len(credentials) == 2
    assert credentials[-1].ativo is True
    assert credentials[0].ativo is False
    assert len(versions) >= 2
    assert any(event.event_type == "integrations.credential_rotated" for event in events)


@pytest.mark.asyncio
async def test_sync_log_cria_e_finaliza_job_canonico(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    legacy = await _legacy_sankhya_config(session)
    service = SankhyaSyncService(session)

    log = await service.iniciar_sync_log(legacy.tenant_id, "pessoas", "import")
    job = (
        await session.execute(
            select(IntegrationJob).where(
                IntegrationJob.tenant_id == legacy.tenant_id,
                IntegrationJob.status == IntegrationJobStatus.RUNNING.value,
            )
        )
    ).scalar_one()

    await service.finalizar_sync_log(log.id, True, 12, 0, None, 150.0)

    finished = (
        await session.execute(select(IntegrationJob).where(IntegrationJob.id == job.id))
    ).scalar_one()
    health = (
        await session.execute(
            select(IntegrationHealth).where(IntegrationHealth.tenant_id == legacy.tenant_id)
        )
    ).scalar_one()

    assert finished.status == IntegrationJobStatus.SUCCESS.value
    assert finished.processados == 12
    assert health.status == IntegrationHealthStatus.CONNECTED.value


@pytest.mark.asyncio
async def test_falha_de_sync_atualiza_job_e_health(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    legacy = await _legacy_sankhya_config(session)
    service = SankhyaSyncService(session)
    log = await service.iniciar_sync_log(legacy.tenant_id, "produtos", "import")

    await service.finalizar_sync_log(log.id, False, 0, 1, "falha externa", 90.0)

    failed = (
        (
            await session.execute(
                select(IntegrationJob).where(
                    IntegrationJob.tenant_id == legacy.tenant_id,
                    IntegrationJob.feature_id.is_not(None),
                )
            )
        )
        .scalars()
        .all()[-1]
    )
    health = (
        await session.execute(
            select(IntegrationHealth).where(IntegrationHealth.tenant_id == legacy.tenant_id)
        )
    ).scalar_one()

    assert failed.status == IntegrationJobStatus.FAILED.value
    assert failed.error_message == "falha externa"
    assert health.status == IntegrationHealthStatus.DEGRADED.value


@pytest.mark.asyncio
async def test_status_detalhado_retorna_campos_canonicos_quando_existirem(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    legacy = await _legacy_sankhya_config(session)
    service = SankhyaSyncService(session)
    log = await service.iniciar_sync_log(legacy.tenant_id, "pessoas", "import")
    await service.finalizar_sync_log(log.id, True, 8, 0, None, 120.0)

    payload = await service.obter_status_detalhado(legacy.tenant_id)

    assert payload["configurado"] is True
    assert payload["status_origem"] == "canonical"
    assert payload["health_origem"] == "canonical"
    assert payload["config_id_canonico"] is not None
    assert payload["lifecycle_state"] in {
        IntegrationStatus.CONFIGURED.value,
        IntegrationStatus.ACTIVE.value,
    }
    assert payload["health_status"] == IntegrationHealthStatus.CONNECTED.value
    assert "pessoas" in payload["features_habilitadas"]
    assert any(policy["feature_code"] == "pessoas" for policy in payload["policies_resumidas"])
    assert payload["readiness"]["status"] == "ATENDIDO"
    assert payload["readiness"]["cta_url"] == "/dashboard/settings/integracoes/erp"


@pytest.mark.asyncio
async def test_status_detalhado_usa_fallback_legado_sem_camada_canonica(
    session: AsyncSession,
) -> None:
    tenant_id = await criar_tenant_real(session)
    legacy = SankhyaConfig(
        id=await _next_sankhya_config_id(session),
        tenant_id=tenant_id,
        ws_url="https://erp.example/ws",
        username="usuario",
        password=encrypt_integration_secret("segredo"),
        ativo=True,
        sync_interval=900,
        teste_status="sucesso",
        ultimo_teste=datetime.utcnow(),
    )
    session.add(legacy)
    await session.commit()

    service = SankhyaSyncService(session)
    payload = await service.obter_status_detalhado(tenant_id)
    health = await service.obter_health_detalhado(tenant_id)

    assert payload["status_origem"] == "legacy"
    assert payload["health_origem"] == "legacy"
    assert payload["health_status"] == "CONNECTED"
    assert payload["config_id_canonico"] is None
    assert health["origem"] == "legacy"
    assert health["status"] == "CONNECTED"


@pytest.mark.asyncio
async def test_logs_enriquecidos_correlacionam_job_e_mascaram_payloads(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    legacy = await _legacy_sankhya_config(session)
    service = SankhyaSyncService(session)
    log = await service.iniciar_sync_log(legacy.tenant_id, "produtos", "import")
    await service.finalizar_sync_log(log.id, False, 2, 1, "token expirado", 80.0)

    job = (
        (
            await session.execute(
                select(IntegrationJob).where(IntegrationJob.tenant_id == legacy.tenant_id)
            )
        )
        .scalars()
        .all()[-1]
    )
    job.result_payload = {"token": "segredo", "erro": "token expirado"}
    session.add(job)
    await session.commit()

    logs = await service.listar_logs_enriquecidos(legacy.tenant_id, limit=10)
    jobs = await service.listar_jobs(legacy.tenant_id, limit=10)

    assert logs[0]["integration_job_id"] == str(job.id)
    assert logs[0]["origem_dados"] == "canonical+legacy"
    assert logs[0]["error_payload"]["token"] == "••••••••"
    assert jobs[0]["legacy_log_id"] == log.id
    assert jobs[0]["result_payload"]["token"] == "••••••••"


@pytest.mark.asyncio
async def test_timeline_nao_repete_log_legado_vinculado_ao_job_canonico(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    legacy = await _legacy_sankhya_config(session)
    service = SankhyaSyncService(session)
    log = await service.iniciar_sync_log(legacy.tenant_id, "pessoas", "import")
    await service.finalizar_sync_log(log.id, True, 5, 0, None, 55.0)

    timeline = await service.listar_timeline_operacional(legacy.tenant_id, limit=20)

    job_entries = [item for item in timeline if item["tipo_registro"] == "canonical_job"]
    linked_log_entries = [
        item
        for item in timeline
        if item["tipo_registro"] == "legacy_log"
        and item["correlation_id"] == job_entries[0]["id"].removeprefix("job:")
    ]

    assert len(job_entries) == 1
    assert linked_log_entries == []
    assert any(item["tipo_registro"] == "health_snapshot" for item in timeline)


@pytest.mark.asyncio
async def test_timeline_funciona_apenas_com_legado(
    session: AsyncSession,
) -> None:
    tenant_id = await criar_tenant_real(session)
    legacy = SankhyaConfig(
        id=await _next_sankhya_config_id(session),
        tenant_id=tenant_id,
        ws_url="https://erp.example/ws",
        username="usuario",
        password=encrypt_integration_secret("segredo"),
        ativo=True,
        sync_interval=900,
        teste_status="erro",
        ultimo_teste=datetime.utcnow(),
    )
    log = SankhyaSyncLog(
        tenant_id=tenant_id,
        tipo="produtos",
        operacao="import",
        status="erro",
        registros_processados=2,
        registros_sucesso=1,
        registros_erro=1,
        erro_mensagem="token expirado",
        created_at=datetime.utcnow(),
    )
    session.add(legacy)
    session.add(log)
    await session.commit()

    service = SankhyaSyncService(session)
    timeline = await service.listar_timeline_operacional(tenant_id, limit=20)

    assert any(item["tipo_registro"] == "legacy_log" for item in timeline)
    assert any(item["tipo_registro"] == "health_snapshot" for item in timeline)


@pytest.mark.asyncio
async def test_diagnostico_calcula_ultimo_sucesso_ultima_falha_e_feature_problematica(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )

    legacy = await _legacy_sankhya_config(session)
    service = SankhyaSyncService(session)
    success_log = await service.iniciar_sync_log(legacy.tenant_id, "pessoas", "import")
    await service.finalizar_sync_log(success_log.id, True, 4, 0, None, 40.0)
    failed_log = await service.iniciar_sync_log(legacy.tenant_id, "produtos", "import")
    await service.finalizar_sync_log(failed_log.id, False, 2, 1, "erro externo", 50.0)

    diagnostico = await service.obter_diagnostico_operacional(legacy.tenant_id)

    assert diagnostico["ultimo_sucesso_at"] is not None
    assert diagnostico["ultima_falha_at"] is not None
    assert diagnostico["jobs_falhos"] >= 1
    assert diagnostico["feature_mais_problematica"] == "produtos"
    assert diagnostico["recomendacao_operacional"]


class _FakeWSClient:
    def __init__(self, _config: SankhyaConfig) -> None:
        self.calls: list[tuple[str, str]] = []

    async def __aenter__(self) -> _FakeWSClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def executar_ws(
        self,
        service: str,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append((service, method))
        return {"success": True, "sankhya_id": "123", "nfe": [], "lancamentos": []}


@pytest.mark.asyncio
async def test_falha_externa_longa_nao_quebra_persistencia_do_health(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )
    legacy = await _legacy_sankhya_config(session)
    service = SankhyaSyncService(session)
    log = await service.iniciar_sync_log(legacy.tenant_id, "pessoas", "import")
    error_message = "Falha no Gateway Sankhya: " + "path inexistente " * 30

    await service.finalizar_sync_log(log.id, False, 0, 1, error_message, 10.0)

    health = await session.scalar(
        select(IntegrationHealth).where(IntegrationHealth.tenant_id == legacy.tenant_id)
    )
    job = await session.scalar(
        select(IntegrationJob).where(IntegrationJob.id == log.integration_job_id)
    )
    assert health is not None
    assert len(health.summary) == 200
    assert health.summary.endswith("…")
    assert job is not None
    assert job.error_message == error_message


@pytest.mark.asyncio
async def test_nfe_service_conecta_sync_existente_ao_job_canonico(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )
    monkeypatch.setattr(
        "integracoes.sankhya.services.nfe_financeiro_service.SankhyaWSClient",
        _FakeWSClient,
    )

    legacy = await _legacy_sankhya_config(session)
    service = SankhyaNFeService(session)
    result = await service.exportar_nfe(
        legacy.tenant_id,
        {"chave_acesso": "abc", "numero": "1", "valor_total": 10},
    )

    job = (
        (
            await session.execute(
                select(IntegrationJob).where(IntegrationJob.tenant_id == legacy.tenant_id)
            )
        )
        .scalars()
        .all()[-1]
    )

    assert result["success"] is True
    assert job.status == IntegrationJobStatus.SUCCESS.value


def test_sankhya_config_e_sync_log_permancem_intactos() -> None:
    source = (REPO_ROOT / "services/api/integracoes/sankhya/models/__init__.py").read_text(
        encoding="utf-8"
    )

    assert "class SankhyaConfig" in source
    assert "class SankhyaSyncLog" in source


def test_rotas_continuam_compativeis_sem_escopo_unidade_produtiva() -> None:
    source = ROUTERS_FILE.read_text(encoding="utf-8")

    assert '"/sync/pessoas"' in source
    assert '"/sync/produtos"' in source
    assert "unidade_produtiva_id" not in source


@pytest.mark.asyncio
async def test_sync_service_reaproveita_config_existente_em_colisao_unica(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = "tenant-concorrencia-sync"
    existing = SankhyaConfig(id=41, tenant_id=tenant_id, sync_interval=900)

    class _FakeSession:
        def __init__(self) -> None:
            self.bind = None

        def add(self, _obj: Any) -> None:
            return None

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

        async def refresh(self, _obj: Any) -> None:
            return None

    service = SankhyaSyncService(_FakeSession())
    service._supports_legacy_gateway_columns = True

    class _Adapter:
        def __init__(self) -> None:
            self.calls: list[tuple[SankhyaConfig, dict[str, Any]]] = []

        async def sync_provider_config(
            self,
            config: SankhyaConfig,
            **kwargs: Any,
        ) -> SankhyaConfig:
            self.calls.append((config, kwargs))
            return config

    adapter_mock = _Adapter()

    async def fake_next_config_id() -> int:
        return 41

    async def fake_get_config(_tenant_id: str) -> SankhyaConfig:
        return existing

    async def fake_restore_rls_context(_tenant_id: str) -> None:
        return None

    async def fake_refresh(_config: Any) -> None:
        return None

    commit_calls = 0

    async def fake_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 1:
            raise IntegrityError(
                "INSERT",
                {},
                sqlite3.IntegrityError("UNIQUE constraint failed: sankhya_config.tenant_id"),
            )
        return None

    async def fake_rollback() -> None:
        return None

    def fake_add(_obj: Any) -> None:
        return None

    monkeypatch.setattr(service, "adapter", adapter_mock)
    monkeypatch.setattr(service, "_next_config_id", fake_next_config_id)
    monkeypatch.setattr(service, "get_config", fake_get_config)
    monkeypatch.setattr(service, "_restore_rls_context", fake_restore_rls_context)
    monkeypatch.setattr(service.db, "add", fake_add)
    monkeypatch.setattr(service.db, "refresh", fake_refresh)
    monkeypatch.setattr(service.db, "commit", fake_commit)
    monkeypatch.setattr(service.db, "rollback", fake_rollback)

    result = await service.criar_config(
        tenant_id,
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/auth",
        sankhya_client_id="client-123",
        sankhya_client_secret="client-secret",
        sankhya_x_token="x-token",
        sync_interval=900,
    )

    assert result.id == existing.id
    assert result.tenant_id == tenant_id
    assert len(adapter_mock.calls) == 1
    assert adapter_mock.calls[0][0].id == existing.id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("constraint_names", "sqlite_message"),
    [
        (
            {
                "uq_tenant_integracoes_provider_scope_tenant",
                "uq_tenant_integracoes_provider_scope_estabelecimento",
            },
            (
                "UNIQUE constraint failed: tenant_integracoes.tenant_id, "
                "tenant_integracoes.integracao_id"
            ),
        ),
        (
            {"uq_tenant_integracoes_provider_scope_estabelecimento"},
            (
                "UNIQUE constraint failed: tenant_integracoes.tenant_id, "
                "tenant_integracoes.integracao_id, tenant_integracoes.scope_id"
            ),
        ),
    ],
)
async def test_adapter_persist_with_unique_retry_reaproveita_linha_existente(
    constraint_names: set[str],
    sqlite_message: str,
) -> None:
    class _FakeNestedTransaction:
        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    class _FakeSession:
        async def begin_nested(self) -> _FakeNestedTransaction:
            return _FakeNestedTransaction()

    adapter = SankhyaCanonicalAdapter(_FakeSession())
    existing = object()
    calls = 0

    async def create_fn() -> object:
        nonlocal calls
        calls += 1
        raise IntegrityError("INSERT", {}, sqlite3.IntegrityError(sqlite_message))

    async def reread_fn() -> object | None:
        return existing

    result, created = await adapter._persist_with_unique_retry(
        label="tenant_integracao_create",
        unique_constraints=constraint_names,
        create_fn=create_fn,
        reread_fn=reread_fn,
        tenant_id="tenant-concorrencia",
        provider_slug="sankhya",
        scope_type=IntegrationScope.TENANT.value,
    )

    assert result is existing
    assert created is False
    assert calls == 1


@pytest.mark.asyncio
async def test_adapter_persist_with_unique_retry_propagates_other_integrity_errors() -> None:
    class _FakeNestedTransaction:
        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    class _FakeSession:
        async def begin_nested(self) -> _FakeNestedTransaction:
            return _FakeNestedTransaction()

    adapter = SankhyaCanonicalAdapter(_FakeSession())

    async def create_fn() -> object:
        raise IntegrityError(
            "INSERT",
            {},
            type("_Orig", (), {"sqlstate": "23503", "constraint_name": "fk_other"})(),
        )

    async def reread_fn() -> object | None:
        return None

    with pytest.raises(IntegrityError):
        await adapter._persist_with_unique_retry(
            label="tenant_integracao_create",
            unique_constraints={"uq_tenant_integracoes_provider_scope_tenant"},
            create_fn=create_fn,
            reread_fn=reread_fn,
            tenant_id="tenant-concorrencia",
            provider_slug="sankhya",
            scope_type=IntegrationScope.TENANT.value,
        )


def test_detector_de_conflito_unico_cobre_postgres_e_sqlite() -> None:
    postgres_error = IntegrityError(
        "INSERT",
        {},
        type(
            "_Orig",
            (),
            {"sqlstate": "23505", "constraint_name": "uq_tenant_integracoes_provider_scope_tenant"},
        )(),
    )
    sqlite_error = IntegrityError(
        "INSERT",
        {},
        sqlite3.IntegrityError(
            "UNIQUE constraint failed: tenant_integracoes.tenant_id, "
            "tenant_integracoes.integracao_id"
        ),
    )
    other_error = IntegrityError(
        "INSERT",
        {},
        type("_Orig", (), {"sqlstate": "23503", "constraint_name": "fk_other"})(),
    )

    assert _is_unique_conflict_for_constraints(
        postgres_error,
        {"uq_tenant_integracoes_provider_scope_tenant"},
    )
    assert _is_unique_conflict_for_constraints(
        sqlite_error,
        {"uq_tenant_integracoes_provider_scope_tenant"},
    )
    assert not _is_unique_conflict_for_constraints(
        other_error,
        {"uq_tenant_integracoes_provider_scope_tenant"},
    )


def test_detector_de_conflito_unico_da_config_cobre_tenant_e_pkey() -> None:
    tenant_error = IntegrityError(
        "INSERT",
        {},
        sqlite3.IntegrityError("UNIQUE constraint failed: sankhya_config.tenant_id"),
    )
    pkey_error = IntegrityError(
        "INSERT",
        {},
        sqlite3.IntegrityError("UNIQUE constraint failed: sankhya_config.id"),
    )
    foreign_key_error = IntegrityError(
        "INSERT",
        {},
        type("_Orig", (), {"sqlstate": "23503", "constraint_name": "fk_other"})(),
    )

    assert _is_sankhya_config_unique_conflict(tenant_error)
    assert _is_sankhya_config_unique_conflict(pkey_error)
    assert not _is_sankhya_config_unique_conflict(foreign_key_error)
