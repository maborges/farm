# ruff: noqa: S105, S106
from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import Column, Table, delete, update
from sqlalchemy import Uuid as UUIDType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import Base
from integracoes.erp_readiness_service import ErpReadinessService
from integracoes.models import (
    ExternalRecordAssociation,
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationJob,
    IntegrationSyncPolicy,
    IntegrationVersion,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.sankhya.models import SankhyaConfig
from integracoes.sankhya.services.sync_service import SankhyaSyncService
from integracoes.security import decrypt_integration_secret
REPO_ROOT = Path(__file__).resolve().parents[5]

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
        await conn.run_sync(lambda sync_conn: IntegrationFeature.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationSyncPolicy.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationJob.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: IntegrationHealth.__table__.create(sync_conn))
        await conn.run_sync(lambda sync_conn: ExternalRecordAssociation.__table__.create(sync_conn))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as current:
        yield current

    await engine.dispose()


@pytest.fixture(autouse=True)
def _stub_canonical_events(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_publish(*args, **kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )


def _make_implantacao(
    tenant_id: uuid.UUID,
    *,
    declared: bool = True,
) -> SimpleNamespace:
    payload = {"integracao_erp": True} if declared else {}
    return SimpleNamespace(
        tenant_id=tenant_id,
        owner_usuario_id=uuid.uuid4(),
        status="IN_PROGRESS",
        etapa_atual="DIAGNOSTICO",
        escopo_modulos=payload,
        diagnostico_inicial_snapshot={},
        unidade_produtiva_id=None,
    )


async def _materialize_runtime(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    service = SankhyaSyncService(session)
    await service.criar_config(
        tenant_id=str(tenant_id),
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/authenticate",
        sankhya_client_id="client-123",
        sankhya_client_secret="client-secret",
        sankhya_x_token="x-token",
        sync_interval=900,
    )


@pytest.mark.asyncio
async def test_servico_dispensa_tenant_sem_erp(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    service = ErpReadinessService(session)

    result = await service.avaliar(_make_implantacao(tenant_id, declared=False))

    assert result.status == "DISPENSADO"
    assert result.cta_url == "/dashboard/settings/integracoes/erp"


@pytest.mark.asyncio
async def test_servico_pendente_sem_provider_configurado(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    service = ErpReadinessService(session)

    result = await service.avaliar(_make_implantacao(tenant_id, declared=True))

    assert result.status == "PENDENTE"
    assert "ERP ainda não configurado" in result.pending_items


@pytest.mark.asyncio
async def test_servico_pendente_sem_health(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    await _materialize_runtime(session, tenant_id)
    await session.execute(delete(IntegrationHealth))
    await session.commit()

    service = ErpReadinessService(session)
    result = await service.avaliar(_make_implantacao(tenant_id, declared=True))

    assert result.status == "PENDENTE"
    assert "teste de comunicação ainda não executado" in result.pending_items


@pytest.mark.asyncio
async def test_servico_falha_com_health_critico(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    await _materialize_runtime(session, tenant_id)
    await session.execute(
        update(IntegrationHealth).values(status="AUTH_ERROR")
    )
    await session.commit()

    service = ErpReadinessService(session)
    result = await service.avaliar(_make_implantacao(tenant_id, declared=True))

    assert result.status == "FALHOU"
    assert any("falha crítica" in reason for reason in result.block_reasons)


@pytest.mark.asyncio
async def test_servico_falha_com_capabilities_p0_incompletas(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    await _materialize_runtime(session, tenant_id)
    await session.execute(
        update(IntegrationFeature).where(IntegrationFeature.codigo == "nfe").values(habilitada=False)
    )
    await session.commit()

    service = ErpReadinessService(session)
    result = await service.avaliar(_make_implantacao(tenant_id, declared=True))

    assert result.status == "FALHOU"
    assert any("funções obrigatórias" in reason for reason in result.block_reasons)


@pytest.mark.asyncio
async def test_servico_pendente_com_policies_ausentes(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    await _materialize_runtime(session, tenant_id)
    await session.execute(
        update(IntegrationSyncPolicy)
        .where(IntegrationSyncPolicy.mode == "MANUAL")
        .values(ativa=False)
    )
    await session.commit()

    service = ErpReadinessService(session)
    result = await service.avaliar(_make_implantacao(tenant_id, declared=True))

    assert result.status == "PENDENTE"
    assert any("regra de atualização pendente" in item for item in result.pending_items)


@pytest.mark.asyncio
async def test_servico_falha_com_conflito_critico(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    await _materialize_runtime(session, tenant_id)
    runtime = await ErpReadinessService(session).carregar_runtime(_make_implantacao(tenant_id, declared=True))
    assert runtime.config is not None and runtime.provider is not None
    session.add(
        ExternalRecordAssociation(
            tenant_id=str(tenant_id),
            provider_id=runtime.provider.id,
            config_id=runtime.config.id,
            environment="producao",
            scope_type="TENANT",
            local_entity="pessoa",
            external_entity="cliente",
            external_record_id="ext-1",
            status="CONFLICT",
            origin="SYNC_JOB",
            confidence="HIGH",
        )
    )
    await session.commit()

    service = ErpReadinessService(session)
    result = await service.avaliar(_make_implantacao(tenant_id, declared=True))

    assert result.status == "FALHOU"
    assert result.conflict_links == 1


@pytest.mark.asyncio
async def test_servico_pendente_com_reconciliacao_pendente(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    await _materialize_runtime(session, tenant_id)
    runtime = await ErpReadinessService(session).carregar_runtime(_make_implantacao(tenant_id, declared=True))
    assert runtime.config is not None and runtime.provider is not None
    session.add(
        ExternalRecordAssociation(
            tenant_id=str(tenant_id),
            provider_id=runtime.provider.id,
            config_id=runtime.config.id,
            environment="producao",
            scope_type="TENANT",
            local_entity="pessoa",
            external_entity="cliente",
            external_record_id="ext-2",
            status="PENDING",
            origin="SYNC_JOB",
            confidence="HIGH",
        )
    )
    await session.commit()

    service = ErpReadinessService(session)
    result = await service.avaliar(_make_implantacao(tenant_id, declared=True))

    assert result.status == "PENDENTE"
    assert result.pending_links == 1


@pytest.mark.asyncio
async def test_servico_atendido_quando_tudo_ok(session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    await _materialize_runtime(session, tenant_id)
    service = ErpReadinessService(session)

    result = await service.avaliar(_make_implantacao(tenant_id, declared=True))

    assert result.status == "ATENDIDO"
    assert result.cta_url == "/dashboard/settings/integracoes/erp"
    assert "piloto inicial" in result.description
    assert result.provider_display_name == "Sankhya ERP"


def test_servico_nao_adota_escopo_unidade_produtiva() -> None:
    source = REPO_ROOT.joinpath("services/api/integracoes/erp_readiness_service.py").read_text(
        encoding="utf-8"
    )

    assert "IntegrationScope.TENANT.value" in source
    assert "IntegrationScope.ESTABELECIMENTO.value" in source
    assert "unidade_produtiva_id" not in source
