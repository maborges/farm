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
from integracoes.erp.provider_registry import ErpProviderRegistry
from integracoes.models import MarketplaceIntegracao
from integracoes.schemas import ProviderSchemaResponse


class _StubSankhyaRuntime:
    """Stub que simula o SankhyaProviderRuntime para testes do router."""

    def __init__(self, session: Any = None) -> None:
        self._session = session
        self._status_response: dict[str, Any] = {}
        self._health_response: dict[str, Any] = {}
        self._jobs_response: list[dict[str, Any]] = []
        self._timeline_response: list[dict[str, Any]] = []
        self._diagnosis_response: dict[str, Any] = {}

    @property
    def provider_slug(self) -> str:
        return "sankhya"

    async def get_status(self, tenant_id: str) -> dict[str, Any]:
        return self._status_response

    async def get_health(self, tenant_id: str) -> dict[str, Any]:
        return self._health_response

    async def get_jobs(self, tenant_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return self._jobs_response

    async def get_timeline(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        feature_code: str | None = None,
        origem: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._timeline_response

    async def get_diagnosis(self, tenant_id: str) -> dict[str, Any]:
        return self._diagnosis_response

    async def get_capabilities(self, tenant_id: str) -> list[dict[str, Any]]:
        return []


# Configurável stub global para uso nos testes
_active_stub: _StubSankhyaRuntime | None = None


def _stub_factory(session: Any) -> _StubSankhyaRuntime:
    """Factory para o registry que retorna o stub ativo."""
    return _active_stub or _StubSankhyaRuntime(session)


@pytest_asyncio.fixture()
async def session() -> Any:
    db = AsyncMock()
    db.info = {}
    db.bind = MagicMock()
    db.bind.dialect.name = "sqlite"
    return db


def _setup_sankhya_registry(monkeypatch: pytest.MonkeyPatch) -> ErpProviderRegistry:
    """Cria registry isolado com sankhya registrado como stub."""
    registry = ErpProviderRegistry()
    registry.register("sankhya", _stub_factory)
    monkeypatch.setattr(erp_router_module, "erp_provider_registry", registry)
    return registry


def _patch_runtime_canonical(
    monkeypatch: pytest.MonkeyPatch,
    tenant_id: uuid.UUID,
    slug: str = "sankhya",
) -> None:
    """Patch carregar_runtime para retornar provider canônico."""

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(
            provider=SimpleNamespace(slug=slug),
            config=SimpleNamespace(id=1),
        )

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)


def _patch_runtime_empty(monkeypatch: pytest.MonkeyPatch, tenant_id: uuid.UUID) -> None:
    """Patch carregar_runtime para retornar sem provider."""

    async def fake_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        assert implantacao.tenant_id == tenant_id
        return SimpleNamespace(provider=None, config=None)

    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_runtime)


@pytest.mark.asyncio
async def test_status_erp_delega_para_servico_sankhya(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    global _active_stub
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    stub = _StubSankhyaRuntime(session)
    stub._status_response = {"configurado": True, "status_origem": "canonical"}
    _active_stub = stub

    _patch_runtime_canonical(monkeypatch, tenant_id)
    _setup_sankhya_registry(monkeypatch)

    response = await erp_router_module.obter_status_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response == {"configurado": True, "status_origem": "canonical"}
    _active_stub = None


@pytest.mark.asyncio
async def test_health_erp_delega_para_servico_sankhya(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    global _active_stub
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    stub = _StubSankhyaRuntime(session)
    stub._health_response = {"configurado": True, "origem": "canonical", "status": "CONNECTED"}
    _active_stub = stub

    _patch_runtime_canonical(monkeypatch, tenant_id)
    _setup_sankhya_registry(monkeypatch)

    response = await erp_router_module.obter_health_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response == {
        "configurado": True,
        "origem": "canonical",
        "status": "CONNECTED",
    }
    _active_stub = None


@pytest.mark.asyncio
async def test_jobs_erp_delega_para_servico_sankhya_com_limit(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    global _active_stub
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    stub = _StubSankhyaRuntime(session)
    stub._jobs_response = [{"id": "job-1", "job_status": "SUCCESS"}]
    _active_stub = stub

    _patch_runtime_canonical(monkeypatch, tenant_id)
    _setup_sankhya_registry(monkeypatch)

    response = await erp_router_module.listar_jobs_erp(
        limit=7,
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response == [{"id": "job-1", "job_status": "SUCCESS"}]
    _active_stub = None


@pytest.mark.asyncio
async def test_sync_completo_erp_dispara_pessoas_e_produtos(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste do sync completo — opera no router Sankhya (provider-specific)."""
    tenant_id = uuid.uuid4()

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

    async def fake_importar_pessoas(
        self: object,
        tenant_scope: str,
        log_id: int | None = None,
    ) -> int:
        assert tenant_scope == str(tenant_id)
        assert log_id == 11
        return 3

    async def fake_importar_produtos(
        self: object,
        tenant_scope: str,
        log_id: int | None = None,
    ) -> int:
        assert tenant_scope == str(tenant_id)
        assert log_id == 22
        return 5

    monkeypatch.setattr(sankhya_router_module.SankhyaSyncService, "get_config", fake_get_config)
    monkeypatch.setattr(
        sankhya_router_module.SankhyaSyncService,
        "iniciar_sync_log",
        fake_iniciar_sync_log,
    )
    monkeypatch.setattr(
        sankhya_router_module.SankhyaSyncService,
        "finalizar_sync_log",
        fake_finalizar_sync_log,
    )
    monkeypatch.setattr(
        sankhya_router_module.SankhyaPessoaService,
        "importar_pessoas",
        fake_importar_pessoas,
    )
    monkeypatch.setattr(
        sankhya_router_module.SankhyaProdutoService,
        "importar_produtos",
        fake_importar_produtos,
    )

    from integracoes.sankhya.services import SankhyaPessoaService, SankhyaProdutoService, SankhyaSyncService

    response = await sankhya_router_module.sincronizar_completo(
        tenant_id=tenant_id,
        sync_service=SankhyaSyncService(session),
        pessoa_service=SankhyaPessoaService(session),
        produto_service=SankhyaProdutoService(session),
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
    global _active_stub
    expected_tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    stub = _StubSankhyaRuntime(session)
    stub._timeline_response = [
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
    _active_stub = stub

    _patch_runtime_canonical(monkeypatch, expected_tenant_id)
    _setup_sankhya_registry(monkeypatch)

    response = cast(
        list[dict[str, Any]],
        await erp_router_module.listar_timeline_erp(
            status="SUCCESS",
            feature_code="produtos",
            origem="canonical",
            limit=9,
            tenant_id=expected_tenant_id,
            readiness_service=readiness_service,
            db=session,
        ),
    )

    assert response[0]["id"] == "evt-1"
    assert response[0]["status"] == "SUCCESS"
    _active_stub = None


@pytest.mark.asyncio
async def test_diagnostico_erp_delega_para_router_sankhya(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    global _active_stub
    expected_tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    stub = _StubSankhyaRuntime(session)
    stub._diagnosis_response = {
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
    _active_stub = stub

    _patch_runtime_canonical(monkeypatch, expected_tenant_id)
    _setup_sankhya_registry(monkeypatch)

    response = cast(
        dict[str, Any],
        await erp_router_module.obter_diagnostico_erp(
            tenant_id=expected_tenant_id,
            readiness_service=readiness_service,
            db=session,
        ),
    )

    assert response["origem"] == "canonical"
    assert response["health_atual"] == "CONNECTED"
    _active_stub = None


@pytest.mark.asyncio
async def test_status_erp_usa_fallback_legacy_sankhya_quando_runtime_ainda_nao_existe(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    global _active_stub
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    stub = _StubSankhyaRuntime(session)
    stub._status_response = {"configurado": True, "status_origem": "legacy", "readiness": {}}
    _active_stub = stub

    _patch_runtime_empty(monkeypatch, tenant_id)
    monkeypatch.setattr(
        erp_router_module,
        "resolve_legacy_sankhya_provider",
        AsyncMock(return_value=True),
    )
    _setup_sankhya_registry(monkeypatch)

    response = await erp_router_module.obter_status_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response["configurado"] is True
    assert response["status_origem"] == "legacy"
    assert response["readiness"]["provider_code"] == "sankhya"
    _active_stub = None


@pytest.mark.asyncio
async def test_status_erp_retorna_estado_vazio_quando_nao_ha_runtime_nem_compatibilidade_legacy(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    _patch_runtime_empty(monkeypatch, tenant_id)
    monkeypatch.setattr(
        erp_router_module,
        "resolve_legacy_sankhya_provider",
        AsyncMock(return_value=False),
    )

    response = await erp_router_module.obter_status_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response["configurado"] is False
    assert response["status_conexao"] == "NOT_CONFIGURED"
    assert response["status_origem"] == "UNCONFIGURED"
    assert response["provider_definition"] is None
    assert response["readiness"]["status"] == "NOT_CONFIGURED"
    assert response["readiness"]["provider_code"] is None


@pytest.mark.asyncio
async def test_health_erp_retorna_estado_vazio_quando_nao_ha_runtime_nem_compatibilidade_legacy(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    _patch_runtime_empty(monkeypatch, tenant_id)
    monkeypatch.setattr(
        erp_router_module,
        "resolve_legacy_sankhya_provider",
        AsyncMock(return_value=False),
    )

    response = await erp_router_module.obter_health_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response == {
        "configurado": False,
        "origem": "UNCONFIGURED",
        "status": "NOT_CONFIGURED",
        "summary": "Integração ainda não configurada.",
        "checked_at": None,
        "last_success_at": None,
        "last_failure_at": None,
        "consecutive_failures": 0,
        "details": None,
    }


@pytest.mark.asyncio
async def test_jobs_erp_retorna_lista_vazia_quando_nao_ha_runtime_nem_compatibilidade_legacy(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    _patch_runtime_empty(monkeypatch, tenant_id)
    monkeypatch.setattr(
        erp_router_module,
        "resolve_legacy_sankhya_provider",
        AsyncMock(return_value=False),
    )

    response = await erp_router_module.listar_jobs_erp(
        limit=7,
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response == []


@pytest.mark.asyncio
async def test_timeline_erp_retorna_lista_vazia_quando_nao_ha_runtime_nem_compatibilidade_legacy(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    _patch_runtime_empty(monkeypatch, tenant_id)
    monkeypatch.setattr(
        erp_router_module,
        "resolve_legacy_sankhya_provider",
        AsyncMock(return_value=False),
    )

    response = await erp_router_module.listar_timeline_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response == []


@pytest.mark.asyncio
async def test_diagnostico_erp_retorna_estado_vazio_sem_runtime_ou_legacy(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    _patch_runtime_empty(monkeypatch, tenant_id)
    monkeypatch.setattr(
        erp_router_module,
        "resolve_legacy_sankhya_provider",
        AsyncMock(return_value=False),
    )

    response = await erp_router_module.obter_diagnostico_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )

    assert response == {
        "origem": "UNCONFIGURED",
        "health_atual": "NOT_CONFIGURED",
        "status_degradacao": "NONE",
        "ultimo_sucesso_at": None,
        "ultima_falha_at": None,
        "falhas_consecutivas": 0,
        "feature_mais_problematica": None,
        "jobs_pendentes": 0,
        "jobs_falhos": 0,
        "recomendacao_operacional": (
            "Selecione um provider no Console ERP e salve a configuração inicial para liberar "
            "a operação."
        ),
    }


@pytest.mark.asyncio
async def test_status_erp_retorna_501_para_provider_sem_runtime_registrado(
    session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    readiness_service = erp_router_module.ErpReadinessService(session)

    _patch_runtime_canonical(monkeypatch, tenant_id, slug="sap")

    # Registry vazio — sap não registrado
    test_registry = ErpProviderRegistry()
    monkeypatch.setattr(erp_router_module, "erp_provider_registry", test_registry)

    with pytest.raises(HTTPException) as exc_info:
        await erp_router_module.obter_status_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

    assert exc_info.value.status_code == 501
    assert "sap" in str(exc_info.value.detail)


def test_main_registra_router_erp() -> None:
    source = (Path(__file__).resolve().parents[3] / "main.py").read_text(encoding="utf-8")

    assert "from integracoes.erp.router import router as erp_router" in source
    assert 'app.include_router(erp_router, prefix="/api/v1/integracoes")' in source


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
        connection_schema={
            "required": ["x"],
            "optional": [],
            "fields": [{"key": "x", "label": "Campo X", "type": "string"}],
        },
        credential_schema={
            "required": ["y"],
            "optional": [],
            "fields": [{"key": "y", "label": "Campo Y", "type": "secret", "secret": True}],
        },
    )
    mock_result.scalar_one_or_none.return_value = mock_provider
    db.execute.return_value = mock_result

    response = await erp_router_module.obter_schema_do_provider("sankhya", db)

    assert isinstance(response, ProviderSchemaResponse)
    assert response.provider.slug == "sankhya"
    assert response.provider.provider_type == "ERP"
    assert response.connection_schema == {
        "required": ["x"],
        "optional": [],
        "fields": [{"key": "x", "label": "Campo X", "type": "string"}],
    }
    assert response.credential_schema == {
        "required": ["y"],
        "optional": [],
        "fields": [{"key": "y", "label": "Campo Y", "type": "secret", "secret": True}],
    }

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
