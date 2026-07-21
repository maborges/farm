# ruff: noqa: S105
from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import events.outbox_model  # noqa: F401 - registra domain_event_outbox no Base.metadata
from integracoes.models import (
    ExternalRecordAssociationConfidence,
    ExternalRecordAssociationHistoryEvent,
    ExternalRecordAssociationOrigin,
    ExternalRecordAssociationStatus,
    IntegrationCredential,
    IntegrationFeature,
    IntegrationJob,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncMode,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.schemas import (
    ExternalRecordAssociationCreate,
    ExternalRecordAssociationReconcile,
    ExternalRecordAssociationUpdate,
)
from integracoes.security import encrypt_integration_secret
from integracoes.services import (
    DuplicateAssociationError,
    ExternalRecordAssociationService,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
MIGRATION_FILE = (
    REPO_ROOT
    / "services/api/migrations/versions/20260706_integrations_external_record_links.py"
)


def _is_real_uuid(value: object) -> bool:
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return False
    return True


@pytest.mark.asyncio
async def test_commit_restaura_contexto_rls_antes_do_refresh() -> None:
    tenant_id = str(uuid.uuid4())
    db = SimpleNamespace(
        commit=AsyncMock(),
        execute=AsyncMock(),
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        info={"tenant_id": tenant_id},
    )

    service = ExternalRecordAssociationService(db)  # type: ignore[arg-type]
    await service._commit_preserving_rls()

    db.commit.assert_awaited_once()
    statement, parameters = db.execute.await_args.args
    assert "set_config('app.current_tenant_id'" in str(statement)
    assert parameters == {"tenant_id": tenant_id}


async def _seed_runtime(
    session: AsyncSession,
    *,
    tenant_id: str | None = None,
    provider_slug: str = "sankhya",
    provider_name: str = "Sankhya",
    environment: str = "producao",
) -> dict[str, object]:
    """Cria um tenant real (ou reutiliza um já criado nesta transação, quando
    `tenant_id` já é um UUID real repassado por um `_seed_runtime` anterior) e
    um provider com slug único. Labels fictícias (ex.: "tenant-1", "tenant-a")
    são ignoradas em favor de um UUID novo — ver INTEGRATIONS-TEST-INFRA-02.
    """
    if tenant_id is not None and _is_real_uuid(tenant_id):
        tenant_id = str(tenant_id)
    else:
        tenant_id = str(uuid.uuid4())
        await session.execute(
            text(
                "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, "
                "storage_limite_mb, idioma_padrao, created_at, updated_at) "
                "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now())"
            ),
            {"id": tenant_id, "nome": "Tenant Association Teste", "doc": tenant_id[:11]},
        )
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))

    provider = MarketplaceIntegracao(
        nome=provider_name,
        slug=f"{provider_slug}-{uuid.uuid4().hex[:8]}",
        categoria="erp",
        provider_type="ERP",
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)

    credential = IntegrationCredential(
        tenant_id=tenant_id,
        provider_id=provider.id,
        scope_type=IntegrationScope.TENANT.value,
        segredo_criptografado=encrypt_integration_secret("segredo"),
        version_number=1,
    )
    session.add(credential)
    await session.commit()
    await session.refresh(credential)

    config = TenantIntegracao(
        tenant_id=tenant_id,
        integracao_id=provider.id,
        scope_type=IntegrationScope.TENANT.value,
        lifecycle_state=IntegrationStatus.ACTIVE.value,
        credential_ref_id=credential.id,
        connection_payload={"environment": environment},
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)

    feature = IntegrationFeature(
        tenant_id=tenant_id,
        config_id=config.id,
        provider_id=provider.id,
        codigo="pessoas",
        nome="Pessoas",
        habilitada=True,
    )
    session.add(feature)
    await session.commit()
    await session.refresh(feature)

    policy = IntegrationSyncPolicy(
        tenant_id=tenant_id,
        config_id=config.id,
        feature_id=feature.id,
        provider_id=provider.id,
        mode=IntegrationSyncMode.MANUAL.value,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)

    job = IntegrationJob(
        tenant_id=tenant_id,
        config_id=config.id,
        feature_id=feature.id,
        sync_policy_id=policy.id,
        provider_id=provider.id,
        status="SUCCESS",
        trigger_type="MANUAL",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    return {
        "provider": provider,
        "credential": credential,
        "config": config,
        "feature": feature,
        "policy": policy,
        "job": job,
    }


def _create_payload(
    *,
    tenant_id: str,
    provider_id: int,
    config_id: int,
    feature_id: int,
    environment: str = "producao",
    local_record_id: str = "pessoa-local-1",
    external_record_id: str = "123",
    external_company_id: str | None = None,
    external_branch_id: str | None = None,
    last_job_id=None,
) -> ExternalRecordAssociationCreate:
    return ExternalRecordAssociationCreate(
        tenant_id=str(tenant_id),
        provider_id=provider_id,
        config_id=config_id,
        feature_id=feature_id,
        environment=environment,
        local_entity="Pessoa",
        local_record_id=local_record_id,
        external_entity="Parceiro",
        external_record_id=external_record_id,
        external_company_id=external_company_id,
        external_branch_id=external_branch_id,
        secondary_keys={"cpf_cnpj": "12345678901"},
        origin=ExternalRecordAssociationOrigin.IMPORT,
        confidence=ExternalRecordAssociationConfidence.HIGH,
        last_job_id=last_job_id,
    )


@pytest.mark.asyncio
async def test_cria_associacao_e_historico(session: AsyncSession) -> None:
    runtime = await _seed_runtime(session)
    service = ExternalRecordAssociationService(session)

    association = await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            last_job_id=runtime["job"].id,
        )
    )

    assert association.status == ExternalRecordAssociationStatus.ACTIVE.value
    assert association.origin == ExternalRecordAssociationOrigin.IMPORT.value
    history = await service.list_history(
        tenant_id=runtime["config"].tenant_id,
        link_id=association.id,
    )
    assert len(history) == 1
    assert history[0].event_type == ExternalRecordAssociationHistoryEvent.CREATED.value


@pytest.mark.asyncio
async def test_consulta_local_e_externa_respeita_provider_ambiente_empresa_filial(
    session: AsyncSession,
) -> None:
    runtime = await _seed_runtime(session)
    service = ExternalRecordAssociationService(session)
    association = await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            external_company_id="10",
            external_branch_id="20",
        )
    )

    by_external = await service.find_local_by_external(
        tenant_id=runtime["config"].tenant_id,
        provider_id=runtime["provider"].id,
        environment="producao",
        external_entity="Parceiro",
        external_record_id="123",
        external_company_id="10",
        external_branch_id="20",
        config_id=runtime["config"].id,
    )
    by_local = await service.find_external_by_local(
        tenant_id=runtime["config"].tenant_id,
        environment="producao",
        local_entity="Pessoa",
        local_record_id="pessoa-local-1",
        external_entity="Parceiro",
        provider_id=runtime["provider"].id,
        config_id=runtime["config"].id,
    )

    assert by_external is not None
    assert by_external.id == association.id
    assert by_local is not None
    assert by_local.external_record_id == "123"


@pytest.mark.asyncio
async def test_detecta_duplicidade_externa_no_mesmo_contexto(session: AsyncSession) -> None:
    runtime = await _seed_runtime(session)
    service = ExternalRecordAssociationService(session)
    await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            last_job_id=runtime["job"].id,
        )
    )

    with pytest.raises(DuplicateAssociationError):
        await service.create_association(
            _create_payload(
                tenant_id=runtime["config"].tenant_id,
                provider_id=runtime["provider"].id,
                config_id=runtime["config"].id,
                feature_id=runtime["feature"].id,
                local_record_id="pessoa-local-2",
                last_job_id=runtime["job"].id,
            )
        )


@pytest.mark.asyncio
async def test_detecta_duplicidade_local_no_mesmo_contexto(session: AsyncSession) -> None:
    runtime = await _seed_runtime(session)
    service = ExternalRecordAssociationService(session)
    await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
        )
    )

    with pytest.raises(DuplicateAssociationError):
        await service.create_association(
            _create_payload(
                tenant_id=runtime["config"].tenant_id,
                provider_id=runtime["provider"].id,
                config_id=runtime["config"].id,
                feature_id=runtime["feature"].id,
                external_record_id="999",
            )
        )


@pytest.mark.asyncio
async def test_permited_mesmo_codigo_em_tenants_diferentes(session: AsyncSession) -> None:
    first = await _seed_runtime(session, tenant_id="tenant-a", provider_slug="provider-a")
    second = await _seed_runtime(session, tenant_id="tenant-b", provider_slug="provider-b")
    service = ExternalRecordAssociationService(session)

    await session.execute(text(f"SET app.current_tenant_id = '{first['config'].tenant_id}'"))
    one = await service.create_association(
        _create_payload(
            tenant_id=first["config"].tenant_id,
            provider_id=first["provider"].id,
            config_id=first["config"].id,
            feature_id=first["feature"].id,
        )
    )
    await session.execute(text(f"SET app.current_tenant_id = '{second['config'].tenant_id}'"))
    two = await service.create_association(
        _create_payload(
            tenant_id=second["config"].tenant_id,
            provider_id=second["provider"].id,
            config_id=second["config"].id,
            feature_id=second["feature"].id,
        )
    )

    assert one.id != two.id
    assert one.external_record_id == two.external_record_id


@pytest.mark.asyncio
async def test_permited_mesmo_codigo_em_ambientes_diferentes(session: AsyncSession) -> None:
    runtime = await _seed_runtime(session)
    service = ExternalRecordAssociationService(session)

    prod = await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            environment="producao",
        )
    )
    homolog = await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            environment="homologacao",
        )
    )

    assert prod.id != homolog.id


@pytest.mark.asyncio
async def test_permited_mesmo_codigo_em_providers_diferentes(session: AsyncSession) -> None:
    first = await _seed_runtime(session, provider_slug="sankhya", provider_name="Sankhya")
    second = await _seed_runtime(
        session,
        tenant_id=first["config"].tenant_id,
        provider_slug="sap",
        provider_name="SAP",
    )
    service = ExternalRecordAssociationService(session)

    one = await service.create_association(
        _create_payload(
            tenant_id=first["config"].tenant_id,
            provider_id=first["provider"].id,
            config_id=first["config"].id,
            feature_id=first["feature"].id,
        )
    )
    two = await service.create_association(
        _create_payload(
            tenant_id=second["config"].tenant_id,
            provider_id=second["provider"].id,
            config_id=second["config"].id,
            feature_id=second["feature"].id,
        )
    )

    assert one.provider_id != two.provider_id
    assert one.external_record_id == two.external_record_id


@pytest.mark.asyncio
async def test_permited_mesmo_codigo_em_empresas_diferentes(session: AsyncSession) -> None:
    runtime = await _seed_runtime(session)
    service = ExternalRecordAssociationService(session)

    first = await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            external_company_id="1",
            external_branch_id="1",
        )
    )
    second = await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            local_record_id="pessoa-local-2",
            external_company_id="2",
            external_branch_id="1",
        )
    )

    assert first.id != second.id


@pytest.mark.asyncio
async def test_atualiza_associacao_e_registra_historico(session: AsyncSession) -> None:
    runtime = await _seed_runtime(session)
    service = ExternalRecordAssociationService(session)
    association = await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
        )
    )

    updated = await service.update_association(
        association,
        ExternalRecordAssociationUpdate(
            notes="ajuste operacional",
            confidence=ExternalRecordAssociationConfidence.MANUAL_CONFIRMED,
            actor_usuario_id="user-1",
            reason="review",
        ),
    )

    assert updated.notes == "ajuste operacional"
    assert updated.confidence == ExternalRecordAssociationConfidence.MANUAL_CONFIRMED.value
    history = await service.list_history(tenant_id=updated.tenant_id, link_id=updated.id)
    assert history[-1].event_type == ExternalRecordAssociationHistoryEvent.UPDATED.value


@pytest.mark.asyncio
async def test_marca_conflito_substitui_desativa_e_reconcilia(session: AsyncSession) -> None:
    runtime = await _seed_runtime(session)
    service = ExternalRecordAssociationService(session)
    association = await service.create_association(
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
        )
    )

    conflict = await service.mark_conflict(
        association,
        actor_usuario_id="user-2",
        reason="codigo duplicado",
        last_job_id=runtime["job"].id,
    )
    assert conflict.status == ExternalRecordAssociationStatus.CONFLICT.value

    reconciled = await service.reconcile_pending(
        conflict,
        ExternalRecordAssociationReconcile(
            actor_usuario_id="user-3",
            reason="validado manualmente",
        ),
    )
    assert reconciled.status == ExternalRecordAssociationStatus.ACTIVE.value
    assert reconciled.confidence == ExternalRecordAssociationConfidence.MANUAL_CONFIRMED.value

    replacement = await service.replace_association(
        reconciled,
        _create_payload(
            tenant_id=runtime["config"].tenant_id,
            provider_id=runtime["provider"].id,
            config_id=runtime["config"].id,
            feature_id=runtime["feature"].id,
            external_record_id="124",
            local_record_id="pessoa-local-2",
        ),
        actor_usuario_id="user-4",
        reason="codigo alterado no ERP",
    )
    assert replacement.status == ExternalRecordAssociationStatus.ACTIVE.value
    assert replacement.external_record_id == "124"

    deactivated = await service.deactivate_association(
        replacement,
        actor_usuario_id="user-5",
        reason="descontinuado",
    )
    assert deactivated.status == ExternalRecordAssociationStatus.INACTIVE.value

    history = await service.list_history(
        tenant_id=association.tenant_id,
        link_id=association.id,
    )
    assert [item.event_type for item in history] == [
        ExternalRecordAssociationHistoryEvent.CREATED.value,
        ExternalRecordAssociationHistoryEvent.CONFLICT_MARKED.value,
        ExternalRecordAssociationHistoryEvent.RECONCILED.value,
        ExternalRecordAssociationHistoryEvent.SUPERSEDED.value,
    ]


def test_enums_e_migration_permanece_estaveis() -> None:
    assert [status.value for status in ExternalRecordAssociationStatus] == [
        "ACTIVE",
        "PENDING",
        "CONFLICT",
        "SUPERSEDED",
        "INACTIVE",
    ]
    assert [event.value for event in ExternalRecordAssociationHistoryEvent] == [
        "CREATED",
        "UPDATED",
        "CONFLICT_MARKED",
        "RECONCILED",
        "SUPERSEDED",
        "DEACTIVATED",
        "REACTIVATED",
    ]

    source = MIGRATION_FILE.read_text(encoding="utf-8")
    assert "integration_external_record_links" in source
    assert "integration_external_record_link_history" in source
    assert "_enable_string_tenant_rls(LINK_TABLE)" in source
    assert "_enable_string_tenant_rls(HISTORY_TABLE)" in source
    assert "uq_external_record_links_active_external" in source
    assert "uq_external_record_links_active_local" in source
