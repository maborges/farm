from __future__ import annotations

# mypy: disable-error-code=attr-defined
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException

import integracoes.erp.router as erp_router_module
import integracoes.sankhya.routers as sankhya_router_module
from integracoes.schemas import ExternalRecordAssociationGovernanceReconcileRequest


@pytest_asyncio.fixture()
async def session() -> Any:
    db = AsyncMock()
    db.info = {}
    db.bind = MagicMock()
    db.bind.dialect.name = "sqlite"
    return db


def _services(session: Any) -> tuple[Any, Any, Any]:
    return (
        erp_router_module.ErpReadinessService(session),
        erp_router_module.SankhyaSyncService(session),
        erp_router_module.ExternalRecordAssociationService(session),
    )


@pytest.mark.asyncio
async def test_status_erp_delega_para_servico_sankhya(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug="sankhya"),
            config=SimpleNamespace(id=1),
        )

    async def fake_status(self: object, tenant_scope: str) -> dict[str, object]:
        assert tenant_scope == str(tenant_id)
        return {"configurado": True, "status_origem": "canonical"}

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(
        erp_router_module.SankhyaSyncService,
        "obter_status_detalhado",
        fake_status,
    )

    response = await erp_router_module.obter_status_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )

    assert response == {"configurado": True, "status_origem": "canonical"}


@pytest.mark.asyncio
async def test_health_erp_delega_para_servico_sankhya(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug="sankhya"),
            config=SimpleNamespace(id=1),
        )

    async def fake_health(self: object, tenant_scope: str) -> dict[str, object]:
        assert tenant_scope == str(tenant_id)
        return {"configurado": True, "origem": "canonical", "status": "CONNECTED"}

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(
        erp_router_module.SankhyaSyncService,
        "obter_health_detalhado",
        fake_health,
    )

    response = await erp_router_module.obter_health_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )

    assert response == {
        "configurado": True,
        "origem": "canonical",
        "status": "CONNECTED",
    }


@pytest.mark.asyncio
async def test_jobs_erp_delega_para_servico_sankhya_com_limit(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug="sankhya"),
            config=SimpleNamespace(id=1),
        )

    async def fake_jobs(
        self: object,
        tenant_scope: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        assert tenant_scope == str(tenant_id)
        assert limit == 7
        return [{"id": "job-1", "job_status": "SUCCESS"}]

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(erp_router_module.SankhyaSyncService, "listar_jobs", fake_jobs)

    response = await erp_router_module.listar_jobs_erp(
        limit=7,
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )

    assert response == [{"id": "job-1", "job_status": "SUCCESS"}]


@pytest.mark.asyncio
async def test_sync_completo_erp_dispara_pessoas_e_produtos(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_get_config(self: object, tenant_scope: str) -> SimpleNamespace | None:
        assert tenant_scope == str(tenant_id)
        return SimpleNamespace(id=1)

    async def fake_iniciar_sync_log(
        self: object,
        tenant_scope: str,
        tipo: str,
        operacao: str,
    ) -> SimpleNamespace:
        assert tenant_scope == str(tenant_id)
        assert operacao == "import"
        return SimpleNamespace(id=11 if tipo == "pessoas" else 22)

    async def fake_finalizar_sync_log(
        self: object,
        log_id: int,
        sucesso: bool,
        processados: int,
        erros: int = 0,
        erro_mensagem: str | None = None,
        tempo_ms: float = 0,
    ) -> None:
        assert log_id in {11, 22}
        assert sucesso is True
        assert erros == 0
        assert erro_mensagem is None

    async def fake_importar_pessoas(self: object, tenant_scope: str, log_id: int | None = None) -> int:
        assert tenant_scope == str(tenant_id)
        assert log_id == 11
        return 3

    async def fake_importar_produtos(self: object, tenant_scope: str, log_id: int | None = None) -> int:
        assert tenant_scope == str(tenant_id)
        assert log_id == 22
        return 5

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(provider=SimpleNamespace(slug="sankhya"), config=SimpleNamespace(id=1))

    monkeypatch.setattr(sankhya_router_module.SankhyaSyncService, "get_config", fake_get_config)
    monkeypatch.setattr(sankhya_router_module.SankhyaSyncService, "iniciar_sync_log", fake_iniciar_sync_log)
    monkeypatch.setattr(sankhya_router_module.SankhyaSyncService, "finalizar_sync_log", fake_finalizar_sync_log)
    monkeypatch.setattr(sankhya_router_module.SankhyaPessoaService, "importar_pessoas", fake_importar_pessoas)
    monkeypatch.setattr(sankhya_router_module.SankhyaProdutoService, "importar_produtos", fake_importar_produtos)

    response = await sankhya_router_module.sincronizar_completo(
        tenant_id=tenant_id,
        sync_service=sankhya_sync_service,
        pessoa_service=sankhya_router_module.SankhyaPessoaService(session),
        produto_service=sankhya_router_module.SankhyaProdutoService(session),
    )

    assert response == {
        "sucesso": True,
        "pessoas_importadas": 3,
        "produtos_importados": 5,
        "mensagem": "Sincronização completa iniciada com sucesso.",
    }



@pytest.mark.asyncio
async def test_timeline_erp_delega_para_router_sankhya_com_filtros(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == expected_tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug="sankhya"),
            config=SimpleNamespace(id=1),
        )

    async def fake_timeline(
        *,
        status: str | None = None,
        feature_code: str | None = None,
        origem: str | None = None,
        limit: int = 50,
        tenant_id: uuid.UUID,
        sync_service: object,
    ) -> list[dict[str, object]]:
        assert tenant_id == expected_tenant_id
        assert sync_service is sankhya_sync_service
        assert status == "SUCCESS"
        assert feature_code == "produtos"
        assert origem == "canonical"
        assert limit == 9
        return [
            {
                "id": "evt-1",
                "tipo_registro": "canonical_job",
                "origem_dado": "canonical",
                "feature_code": "produtos",
                "status": "SUCCESS",
                "event_type": "JOB_FINISHED",
                "resumo": "Sincronizacao concluida",
                "occurred_at": "2026-07-09T10:00:00Z",
                "processados": 10,
                "sucessos": 10,
                "erros": 0,
            }
        ]

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(
        erp_router_module,
        "listar_timeline_sankhya_provider",
        fake_timeline,
    )

    response = cast(
        list[dict[str, Any]],
        await erp_router_module.listar_timeline_erp(
            status="SUCCESS",
            feature_code="produtos",
            origem="canonical",
            limit=9,
            tenant_id=expected_tenant_id,
            readiness_service=readiness_service,
            sankhya_sync_service=sankhya_sync_service,
        ),
    )

    assert response[0]["id"] == "evt-1"
    assert response[0]["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_diagnostico_erp_delega_para_router_sankhya(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == expected_tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug="sankhya"),
            config=SimpleNamespace(id=1),
        )

    async def fake_diagnostico(
        *,
        tenant_id: uuid.UUID,
        sync_service: object,
    ) -> dict[str, object]:
        assert tenant_id == expected_tenant_id
        assert sync_service is sankhya_sync_service
        return {
            "origem": "canonical",
            "health_atual": "CONNECTED",
            "status_degradacao": "estavel",
            "ultimo_sucesso_at": "2026-07-09T10:00:00Z",
            "ultima_falha_at": None,
            "falhas_consecutivas": 0,
            "feature_mais_problematica": None,
            "jobs_pendentes": 0,
            "jobs_falhos": 0,
            "recomendacao_operacional": "Continuar monitoramento.",
        }

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(
        erp_router_module,
        "obter_diagnostico_sankhya_provider",
        fake_diagnostico,
    )

    response = cast(
        dict[str, Any],
        await erp_router_module.obter_diagnostico_erp(
            tenant_id=expected_tenant_id,
            readiness_service=readiness_service,
            sankhya_sync_service=sankhya_sync_service,
        ),
    )

    assert response["origem"] == "canonical"
    assert response["health_atual"] == "CONNECTED"


@pytest.mark.asyncio
async def test_associacoes_pendentes_erp_delega_para_router_sankhya(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, association_service = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug="sankhya"),
            config=SimpleNamespace(id=1),
        )

    async def fake_listar_associacoes(
        *,
        provider_id: int | None = None,
        feature_id: int | None = None,
        feature_code: str | None = None,
        entity_type: str | None = None,
        external_entity_type: str | None = None,
        environment: str | None = None,
        tenant_filter: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
        current_tenant_id: uuid.UUID,
        service: object,
    ) -> list[dict[str, object]]:
        assert current_tenant_id == tenant_id
        assert service is association_service
        assert provider_id == 7
        assert feature_code == "pessoas"
        assert entity_type == "Pessoa"
        assert external_entity_type == "Parceiro"
        assert environment == "producao"
        assert tenant_filter == tenant_id
        assert limit == 11
        assert offset == 3
        return [
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "provider_id": 7,
                "config_id": 9,
                "feature_id": 11,
                "feature_code": "pessoas",
                "environment": "producao",
                "scope_type": "TENANT",
                "scope_id": None,
                "external_company_id": None,
                "external_branch_id": None,
                "local_entity_type": "Pessoa",
                "local_entity_id": None,
                "external_entity_type": "Parceiro",
                "external_id": "1001",
                "external_key": "7|9|producao|Parceiro|-|-|1001",
                "external_payload": {"secondary_keys": {}, "metadata_json": {}},
                "status": "PENDING",
                "confidence": "MEDIUM",
                "motivo": "aguardando validacao",
                "last_sync_at": None,
                "last_job_id": None,
                "created_at": "2026-07-09T10:00:00Z",
                "updated_at": "2026-07-09T10:00:00Z",
                "history": [],
            }
        ]

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(
        erp_router_module,
        "listar_associacoes_externas_pendentes_sankhya",
        fake_listar_associacoes,
    )

    response = cast(
        list[dict[str, Any]],
        await erp_router_module.listar_associacoes_erp_pendentes(
            provider_id=7,
            feature_code="pessoas",
            entity_type="Pessoa",
            external_entity_type="Parceiro",
            environment="producao",
            tenant_filter=tenant_id,
            limit=11,
            offset=3,
            current_tenant_id=tenant_id,
            readiness_service=readiness_service,
            sankhya_sync_service=sankhya_sync_service,
            association_service=association_service,
        ),
    )

    assert response[0]["status"] == "PENDING"
    assert response[0]["feature_code"] == "pessoas"


@pytest.mark.asyncio
async def test_reconciliar_associacao_erp_delega_para_router_sankhya(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    expected_association_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, association_service = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug="sankhya"),
            config=SimpleNamespace(id=1),
        )

    async def fake_reconciliar(
        *,
        association_id: uuid.UUID,
        payload: Any,
        current_tenant_id: uuid.UUID,
        service: object,
    ) -> dict[str, object]:
        assert association_id == expected_association_id
        assert current_tenant_id == tenant_id
        assert service is association_service
        assert payload.local_entity_type == "Pessoa"
        assert payload.local_entity_id == "pessoa-1"
        return {
            "id": str(association_id),
            "tenant_id": str(tenant_id),
            "provider_id": 7,
            "config_id": 9,
            "feature_id": 11,
            "feature_code": "pessoas",
            "environment": "producao",
            "scope_type": "TENANT",
            "scope_id": None,
            "external_company_id": None,
            "external_branch_id": None,
            "local_entity_type": "Pessoa",
            "local_entity_id": "pessoa-1",
            "external_entity_type": "Parceiro",
            "external_id": "2002",
            "external_key": "7|9|producao|Parceiro|-|-|2002",
            "external_payload": {"secondary_keys": {}, "metadata_json": {}},
            "status": "ACTIVE",
            "confidence": "MANUAL_CONFIRMED",
            "motivo": "reconciliado",
            "last_sync_at": None,
            "last_job_id": None,
            "created_at": "2026-07-09T10:00:00Z",
            "updated_at": "2026-07-09T10:01:00Z",
            "history": [],
        }

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(
        erp_router_module,
        "reconciliar_associacao_externa_sankhya",
        fake_reconciliar,
    )

    payload = ExternalRecordAssociationGovernanceReconcileRequest(
        local_entity_type="Pessoa",
        local_entity_id="pessoa-1",
        reason="validado manualmente",
    )
    response = cast(
        dict[str, Any],
        await erp_router_module.reconciliar_associacao_erp(
            association_id=expected_association_id,
            payload=payload,
            current_tenant_id=tenant_id,
            readiness_service=readiness_service,
            sankhya_sync_service=sankhya_sync_service,
            association_service=association_service,
        ),
    )

    assert response["id"] == str(expected_association_id)
    assert response["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_status_erp_usa_fallback_legacy_sankhya_quando_runtime_ainda_nao_existe(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(provider=None, config=None)

    async def fake_get_config(self: object, tenant_scope: str) -> object:
        assert tenant_scope == str(tenant_id)
        return object()

    async def fake_status(self: object, tenant_scope: str) -> dict[str, object]:
        assert tenant_scope == str(tenant_id)
        return {"configurado": True, "status_origem": "legacy"}

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(erp_router_module.SankhyaSyncService, "get_config", fake_get_config)
    monkeypatch.setattr(
        erp_router_module.SankhyaSyncService,
        "obter_status_detalhado",
        fake_status,
    )

    response = await erp_router_module.obter_status_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )

    assert response == {"configurado": True, "status_origem": "legacy"}


@pytest.mark.asyncio
async def test_status_erp_retorna_404_quando_nao_ha_runtime_nem_compatibilidade_legacy(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(provider=None, config=None)

    async def fake_get_config(self: object, tenant_scope: str) -> None:
        assert tenant_scope == str(tenant_id)
        return None

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)
    monkeypatch.setattr(erp_router_module.SankhyaSyncService, "get_config", fake_get_config)

    with pytest.raises(HTTPException) as exc_info:
        await erp_router_module.obter_status_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            sankhya_sync_service=sankhya_sync_service,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "ERP não configurado"


@pytest.mark.asyncio
async def test_status_erp_retorna_501_para_provider_ainda_nao_suportado(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service, sankhya_sync_service, _ = _services(session)

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug="sap"),
            config=SimpleNamespace(id=1),
        )

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)

    with pytest.raises(HTTPException) as exc_info:
        await erp_router_module.obter_status_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            sankhya_sync_service=sankhya_sync_service,
        )

    assert exc_info.value.status_code == 501
    assert "sap" in str(exc_info.value.detail)


def test_main_registra_router_erp() -> None:
    source = (Path(__file__).resolve().parents[3] / "main.py").read_text(encoding="utf-8")

    assert "from integracoes.erp.router import router as erp_router" in source
    assert 'app.include_router(erp_router, prefix="/api/v1/integracoes")' in source
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
import integracoes.erp.router as erp_router_module
from integracoes.schemas import ProviderSchemaResponse
from integracoes.models import MarketplaceIntegracao

@pytest.mark.asyncio
async def test_obter_schema_do_provider_erp_ativo_retorna_200() -> None:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_provider = MarketplaceIntegracao(
        id=10,
        slug="sankhya",
        nome="Sankhya ERP",
        descricao_curta="Desc",
        provider_type="ERP",
        ativa=True,
        oficial=True,
        connection_schema={"required": ["x"], "optional": []},
        credential_schema={"required": ["y"], "optional": []},
    )
    mock_result.scalar_one_or_none.return_value = mock_provider
    db.execute.return_value = mock_result

    response = await erp_router_module.obter_schema_do_provider("sankhya", db)

    assert isinstance(response, ProviderSchemaResponse)
    assert response.provider.slug == "sankhya"
    assert response.provider.provider_type == "ERP"
    assert response.connection_schema.model_dump(exclude_unset=True) == {"required": ["x"], "optional": []}
    assert response.credential_schema.model_dump(exclude_unset=True) == {"required": ["y"], "optional": []}

@pytest.mark.asyncio
async def test_obter_schema_do_provider_rejeita_inexistente() -> None:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await erp_router_module.obter_schema_do_provider("inexistente", db)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_obter_schema_do_provider_rejeita_nao_erp() -> None:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_provider = MarketplaceIntegracao(provider_type="CRM", ativa=True)
    mock_result.scalar_one_or_none.return_value = mock_provider
    db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await erp_router_module.obter_schema_do_provider("crm-slug", db)
    assert exc.value.status_code == 400
    assert "não é do tipo ERP" in exc.value.detail

@pytest.mark.asyncio
async def test_obter_schema_do_provider_rejeita_inativo() -> None:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_provider = MarketplaceIntegracao(provider_type="ERP", ativa=False)
    mock_result.scalar_one_or_none.return_value = mock_provider
    db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await erp_router_module.obter_schema_do_provider("inativo", db)
    assert exc.value.status_code == 400
    assert "está inativo" in exc.value.detail
