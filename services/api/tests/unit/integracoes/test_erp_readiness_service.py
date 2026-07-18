# ruff: noqa: S105, S106
from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.erp_readiness_service import ErpReadinessService
from integracoes.models import (
    ExternalRecordAssociation,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationSyncPolicy,
)
from integracoes.sankhya.services.sync_service import SankhyaSyncService

REPO_ROOT = Path(__file__).resolve().parents[5]


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


async def _criar_tenant_real(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, "
            "storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now())"
        ),
        {"id": str(tenant_id), "nome": "Tenant ERP Readiness", "doc": str(tenant_id)[:11]},
    )
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))


async def _materialize_runtime(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await _criar_tenant_real(session, tenant_id)
    service = SankhyaSyncService(session)
    await service.criar_config(
        tenant_id=str(tenant_id),
        auth_model="gateway_oauth_client_credentials",
        sankhya_environment="producao",
        sankhya_api_base_url="https://public.com/api",
        sankhya_auth_url="https://public.com/authenticate",
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
        update(IntegrationFeature)
        .where(IntegrationFeature.codigo == "nfe")
        .values(habilitada=False)
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
    runtime = await ErpReadinessService(session).carregar_runtime(
        _make_implantacao(tenant_id, declared=True)
    )
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
    runtime = await ErpReadinessService(session).carregar_runtime(
        _make_implantacao(tenant_id, declared=True)
    )
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
