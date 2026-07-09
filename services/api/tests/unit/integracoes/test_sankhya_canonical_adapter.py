# ruff: noqa: S105, S106
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import Column, Table, select
from sqlalchemy import Uuid as UUIDType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import Base
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
from integracoes.sankhya.models import SankhyaConfig, SankhyaNFe, SankhyaSyncLog
from integracoes.sankhya.services.nfe_financeiro_service import SankhyaNFeService
from integracoes.sankhya.services.sync_service import SankhyaSyncService
from integracoes.security import decrypt_integration_secret, encrypt_integration_secret

REPO_ROOT = Path(__file__).resolve().parents[5]
ROUTERS_FILE = REPO_ROOT / "services/api/integracoes/sankhya/routers/__init__.py"

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
        await conn.run_sync(lambda sync_conn: MarketplaceIntegracao.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationCredential.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: TenantIntegracao.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationVersion.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: SankhyaConfig.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: SankhyaSyncLog.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationFeature.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationSyncPolicy.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationJob.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationHealth.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: SankhyaNFe.__table__.create(sync_conn))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as current:
        yield current

    await engine.dispose()


async def _legacy_sankhya_config(session: AsyncSession) -> SankhyaConfig:
    service = SankhyaSyncService(session)
    return await service.criar_config(
        tenant_id="90aa4f2e-c8ce-4e69-a792-eedf505372e4",
        ws_url="https://erp.example/ws",
        username="usuario",
        password="segredo",
        sync_interval=900,
    )


async def _gateway_sankhya_config(session: AsyncSession) -> SankhyaConfig:
    service = SankhyaSyncService(session)
    return await service.criar_config(
        tenant_id="90aa4f2e-c8ce-4e69-a792-eedf505372e4",
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
                select(IntegrationSyncPolicy).where(
                    IntegrationSyncPolicy.config_id == config.id
                )
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
    assert "erp.cadastros.pessoas.importar" in provider.provider_definition["supported_capabilities"]
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
        provider.sync_schema["retry"]["max_attempts_source"]
        == "IntegrationSyncPolicy.max_retries"
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
    assert config.connection_payload["auth_model"] == "GATEWAY"
    assert config.credenciais["auth_model"] == "GATEWAY"
    assert credential_payload["sankhya_client_secret"] == "client-secret"
    assert credential_payload["sankhya_x_token"] == "x-token"


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
        await session.execute(
            select(IntegrationJob).where(
                IntegrationJob.tenant_id == legacy.tenant_id,
                IntegrationJob.feature_id.is_not(None),
            )
        )
    ).scalars().all()[-1]
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


@pytest.mark.asyncio
async def test_status_detalhado_usa_fallback_legado_sem_camada_canonica(
    session: AsyncSession,
) -> None:
    legacy = SankhyaConfig(
        tenant_id="tenant-legado",
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
    payload = await service.obter_status_detalhado("tenant-legado")
    health = await service.obter_health_detalhado("tenant-legado")

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
        await session.execute(
            select(IntegrationJob).where(IntegrationJob.tenant_id == legacy.tenant_id)
        )
    ).scalars().all()[-1]
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
async def test_timeline_retorna_dados_canonicos_e_legados(
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

    assert any(item["tipo_registro"] == "canonical_job" for item in timeline)
    assert any(item["tipo_registro"] == "legacy_log" for item in timeline)
    assert any(item["tipo_registro"] == "health_snapshot" for item in timeline)


@pytest.mark.asyncio
async def test_timeline_funciona_apenas_com_legado(
    session: AsyncSession,
) -> None:
    legacy = SankhyaConfig(
        tenant_id="tenant-legado-2",
        ws_url="https://erp.example/ws",
        username="usuario",
        password=encrypt_integration_secret("segredo"),
        ativo=True,
        sync_interval=900,
        teste_status="erro",
        ultimo_teste=datetime.utcnow(),
    )
    log = SankhyaSyncLog(
        id=1,
        tenant_id="tenant-legado-2",
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
    timeline = await service.listar_timeline_operacional("tenant-legado-2", limit=20)

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
        await session.execute(
            select(IntegrationJob).where(IntegrationJob.tenant_id == legacy.tenant_id)
        )
    ).scalars().all()[-1]

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
