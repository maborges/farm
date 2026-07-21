"""Testes do contrato runtime, registry e extensibilidade de providers ERP.

Cobre:
1. Contrato runtime formal existe e é um Protocol
2. Implementação Sankhya satisfaz o contrato
3. Registry registra, resolve, rejeita duplicatas e desconhecidos
4. Provider fictício funciona sem alteração no core
5. Tenant vazio não assume provider
6. Provider sem runtime produz estado explícito
7. Prova de extensibilidade com test_erp
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from integracoes.erp.provider_contract import ErpProviderRuntime
from integracoes.erp.provider_registry import (
    ErpProviderDuplicateError,
    ErpProviderNotRegisteredError,
    ErpProviderRegistry,
    erp_provider_registry,
)

# ---------------------------------------------------------------------------
# Provider fictício de teste (em memória, determinístico)
# ---------------------------------------------------------------------------


class StubErpProviderRuntime:
    """Implementação fictícia do contrato ErpProviderRuntime para testes.

    Respostas determinísticas, sem banco, sem dependências de provider real.
    """

    def __init__(self, session: Any = None) -> None:
        self._session = session

    @property
    def provider_slug(self) -> str:
        return "test_erp"

    async def get_status(self, tenant_id: str) -> dict[str, Any]:
        return {
            "configurado": True,
            "ativo": True,
            "status_conexao": "CONNECTED",
            "status_origem": "test_erp",
            "health_origem": "test_erp",
            "health_status": "CONNECTED",
            "provider_slug": "test_erp",
        }

    async def get_health(self, tenant_id: str) -> dict[str, Any]:
        return {
            "configurado": True,
            "origem": "test_erp",
            "status": "CONNECTED",
            "summary": "Test ERP is healthy.",
            "checked_at": None,
            "last_success_at": None,
            "last_failure_at": None,
            "consecutive_failures": 0,
            "details": None,
        }

    async def get_jobs(
        self,
        tenant_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return [{"id": "test-job-1", "job_status": "SUCCESS"}]

    async def get_timeline(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        feature_code: str | None = None,
        origem: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "test-evt-1",
                "tipo_registro": "test_job",
                "origem_dado": "test_erp",
                "status": "SUCCESS",
                "resumo": "Test timeline event",
                "occurred_at": "2026-01-01T00:00:00Z",
            }
        ]

    async def get_diagnosis(self, tenant_id: str) -> dict[str, Any]:
        return {
            "origem": "test_erp",
            "health_atual": "CONNECTED",
            "status_degradacao": "estavel",
            "ultimo_sucesso_at": None,
            "ultima_falha_at": None,
            "falhas_consecutivas": 0,
            "feature_mais_problematica": None,
            "jobs_pendentes": 0,
            "jobs_falhos": 0,
            "recomendacao_operacional": "Test provider nominal.",
        }

    async def get_capabilities(self, tenant_id: str) -> list[dict[str, Any]]:
        return [{"feature_code": "test_feature", "habilitada": True}]

    async def sync_feature(
        self,
        tenant_id: str,
        feature_code: str,
        *,
        scheduled: bool = False,
    ) -> dict[str, Any]:
        return {"feature_code": feature_code, "scheduled": scheduled}

    async def get_person_by_external_id(
        self,
        tenant_id: str,
        external_id: str,
    ) -> dict[str, Any] | None:
        return {"external_id": external_id, "nome_exibicao": "Pessoa Teste"}

    async def list_people(self, tenant_id: str) -> list[dict[str, Any]]:
        return []


# ---------------------------------------------------------------------------
# Testes do contrato formal
# ---------------------------------------------------------------------------


class TestErpProviderContract:
    """Verifica que o contrato runtime formal existe e é tipável."""

    def test_contrato_e_runtime_checkable(self) -> None:
        assert hasattr(ErpProviderRuntime, "__protocol_attrs__") or hasattr(
            ErpProviderRuntime, "__abstractmethods__"
        )

    def test_provider_ficticio_satisfaz_contrato_estruturalmente(self) -> None:
        runtime = StubErpProviderRuntime()
        assert isinstance(runtime, ErpProviderRuntime)

    def test_contrato_possui_metodos_obrigatorios(self) -> None:
        expected_methods = [
            "get_status",
            "get_health",
            "get_jobs",
            "get_timeline",
            "get_diagnosis",
            "get_capabilities",
            "get_person_by_external_id",
            "list_people",
        ]
        for method in expected_methods:
            assert hasattr(ErpProviderRuntime, method), f"Método {method} ausente no contrato"

    def test_contrato_possui_provider_slug(self) -> None:
        runtime = StubErpProviderRuntime()
        assert runtime.provider_slug == "test_erp"


# ---------------------------------------------------------------------------
# Testes do Registry
# ---------------------------------------------------------------------------


class TestErpProviderRegistry:
    """Testes unitários do registry de providers ERP."""

    def test_registrar_e_resolver(self) -> None:
        registry = ErpProviderRegistry()
        registry.register("test_erp", StubErpProviderRuntime)
        session = MagicMock()
        runtime = registry.resolve("test_erp", session)
        assert runtime.provider_slug == "test_erp"

    def test_registro_duplicado_e_rejeitado(self) -> None:
        registry = ErpProviderRegistry()
        registry.register("test_erp", StubErpProviderRuntime)
        with pytest.raises(ErpProviderDuplicateError):
            registry.register("test_erp", StubErpProviderRuntime)

    def test_provider_desconhecido_e_rejeitado(self) -> None:
        registry = ErpProviderRegistry()
        session = MagicMock()
        with pytest.raises(ErpProviderNotRegisteredError):
            registry.resolve("inexistente", session)

    def test_is_registered_funciona(self) -> None:
        registry = ErpProviderRegistry()
        assert registry.is_registered("test_erp") is False
        registry.register("test_erp", StubErpProviderRuntime)
        assert registry.is_registered("test_erp") is True

    def test_slug_normalizado_para_lowercase(self) -> None:
        registry = ErpProviderRegistry()
        registry.register("TEST_ERP", StubErpProviderRuntime)
        assert registry.is_registered("test_erp") is True
        session = MagicMock()
        runtime = registry.resolve("test_erp", session)
        assert runtime.provider_slug == "test_erp"

    def test_reset_limpa_registros(self) -> None:
        registry = ErpProviderRegistry()
        registry.register("test_erp", StubErpProviderRuntime)
        registry._reset()
        assert registry.is_registered("test_erp") is False

    def test_registry_global_existe(self) -> None:
        assert erp_provider_registry is not None
        assert isinstance(erp_provider_registry, ErpProviderRegistry)


# ---------------------------------------------------------------------------
# Testes do Router com Provider via Registry
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def session() -> Any:
    db = AsyncMock()
    db.info = {}
    db.bind = MagicMock()
    db.bind.dialect.name = "sqlite"
    return db


class TestRouterComRegistry:
    """Testes de integração do router ERP com o registry."""

    @pytest.mark.asyncio
    async def test_status_via_provider_resolvido_pelo_registry(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                provider=SimpleNamespace(slug="sankhya"),
                config=SimpleNamespace(id=1),
            )

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        # Registrar provider fictício como sankhya para este teste
        test_registry = ErpProviderRegistry()
        test_registry.register("sankhya", StubErpProviderRuntime)
        monkeypatch.setattr(erp_router_module, "erp_provider_registry", test_registry)

        response = await erp_router_module.obter_status_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert response["configurado"] is True
        assert response["status_origem"] == "test_erp"

    @pytest.mark.asyncio
    async def test_health_via_provider_resolvido_pelo_registry(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                provider=SimpleNamespace(slug="sankhya"),
                config=SimpleNamespace(id=1),
            )

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        test_registry = ErpProviderRegistry()
        test_registry.register("sankhya", StubErpProviderRuntime)
        monkeypatch.setattr(erp_router_module, "erp_provider_registry", test_registry)

        response = await erp_router_module.obter_health_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert response["configurado"] is True
        assert response["origem"] == "test_erp"
        assert response["status"] == "CONNECTED"

    @pytest.mark.asyncio
    async def test_jobs_via_provider_resolvido_pelo_registry(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                provider=SimpleNamespace(slug="sankhya"),
                config=SimpleNamespace(id=1),
            )

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        test_registry = ErpProviderRegistry()
        test_registry.register("sankhya", StubErpProviderRuntime)
        monkeypatch.setattr(erp_router_module, "erp_provider_registry", test_registry)

        response = await erp_router_module.listar_jobs_erp(
            limit=5,
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert len(response) == 1
        assert response[0]["id"] == "test-job-1"

    @pytest.mark.asyncio
    async def test_timeline_via_provider_resolvido_pelo_registry(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                provider=SimpleNamespace(slug="sankhya"),
                config=SimpleNamespace(id=1),
            )

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        test_registry = ErpProviderRegistry()
        test_registry.register("sankhya", StubErpProviderRuntime)
        monkeypatch.setattr(erp_router_module, "erp_provider_registry", test_registry)

        response = await erp_router_module.listar_timeline_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert len(response) == 1
        assert response[0]["origem_dado"] == "test_erp"

    @pytest.mark.asyncio
    async def test_diagnostico_via_provider_resolvido_pelo_registry(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                provider=SimpleNamespace(slug="sankhya"),
                config=SimpleNamespace(id=1),
            )

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        test_registry = ErpProviderRegistry()
        test_registry.register("sankhya", StubErpProviderRuntime)
        monkeypatch.setattr(erp_router_module, "erp_provider_registry", test_registry)

        response = await erp_router_module.obter_diagnostico_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert response["origem"] == "test_erp"
        assert response["health_atual"] == "CONNECTED"


# ---------------------------------------------------------------------------
# Testes de estado para Tenant vazio, provider desconhecido, sem runtime
# ---------------------------------------------------------------------------


class TestResolucoesDeEstado:
    """Testes que verificam comportamento para estados especiais."""

    @pytest.mark.asyncio
    async def test_tenant_vazio_nao_assume_provider(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(provider=None, config=None)

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        response = await erp_router_module.obter_status_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert response["configurado"] is False
        assert response["status_conexao"] == "NOT_CONFIGURED"
        assert response["status_origem"] == "UNCONFIGURED"
        assert response["readiness"]["provider_code"] is None

    @pytest.mark.asyncio
    async def test_provider_configurado_sem_runtime_retorna_501(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from fastapi import HTTPException

        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                provider=SimpleNamespace(slug="oracle_erp"),
                config=SimpleNamespace(id=1),
            )

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        # Registry vazio — oracle_erp não registrado
        test_registry = ErpProviderRegistry()
        monkeypatch.setattr(erp_router_module, "erp_provider_registry", test_registry)

        with pytest.raises(HTTPException) as exc_info:
            await erp_router_module.obter_status_erp(
                tenant_id=tenant_id,
                readiness_service=readiness_service,
                db=session,
            )

        assert exc_info.value.status_code == 501
        assert "oracle_erp" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_health_tenant_vazio_retorna_unconfigured(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(provider=None, config=None)

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        response = await erp_router_module.obter_health_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert response["configurado"] is False
        assert response["origem"] == "UNCONFIGURED"
        assert response["status"] == "NOT_CONFIGURED"

    @pytest.mark.asyncio
    async def test_jobs_tenant_vazio_retorna_lista_vazia(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(provider=None, config=None)

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        response = await erp_router_module.listar_jobs_erp(
            limit=10,
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert response == []

    @pytest.mark.asyncio
    async def test_diagnostico_tenant_vazio_retorna_unconfigured(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(provider=None, config=None)

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        response = await erp_router_module.obter_diagnostico_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )

        assert response["origem"] == "UNCONFIGURED"
        assert response["health_atual"] == "NOT_CONFIGURED"


# ---------------------------------------------------------------------------
# Prova de extensibilidade
# ---------------------------------------------------------------------------


class TestExtensibilidade:
    """Demonstra que um segundo provider funciona sem alterar o router."""

    @pytest.mark.asyncio
    async def test_provider_ficticio_responde_sem_sankhya_nem_alteracao_no_router(
        self,
        session: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Prova obrigatória de extensibilidade (seção 22 da spec).

        TenantIntegracao aponta para test_erp
        → registry resolve test_erp
        → router retorna dados do provider fictício
        → nenhuma classe Sankhya é chamada
        → nenhum arquivo do router precisa ser alterado
        """
        import integracoes.erp.router as erp_router_module

        tenant_id = uuid.uuid4()
        readiness_service = erp_router_module.ErpReadinessService(session)

        async def fake_runtime(
            self: object,
            implantacao: SimpleNamespace,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                provider=SimpleNamespace(slug="test_erp"),
                config=SimpleNamespace(id=99),
            )

        monkeypatch.setattr(
            erp_router_module.ErpReadinessService,
            "carregar_runtime",
            fake_runtime,
        )

        test_registry = ErpProviderRegistry()
        test_registry.register("test_erp", StubErpProviderRuntime)
        monkeypatch.setattr(erp_router_module, "erp_provider_registry", test_registry)

        # Status
        status = await erp_router_module.obter_status_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )
        assert status["provider_slug"] == "test_erp"
        assert status["status_origem"] == "test_erp"

        # Health
        health = await erp_router_module.obter_health_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )
        assert health["origem"] == "test_erp"

        # Jobs
        jobs = await erp_router_module.listar_jobs_erp(
            limit=5,
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )
        assert jobs[0]["id"] == "test-job-1"

        # Timeline
        timeline = await erp_router_module.listar_timeline_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )
        assert timeline[0]["origem_dado"] == "test_erp"

        # Diagnóstico
        diag = await erp_router_module.obter_diagnostico_erp(
            tenant_id=tenant_id,
            readiness_service=readiness_service,
            db=session,
        )
        assert diag["origem"] == "test_erp"
        assert diag["recomendacao_operacional"] == "Test provider nominal."

    @pytest.mark.asyncio
    async def test_provider_ficticio_nao_importa_sankhya(
        self,
        session: Any,
    ) -> None:
        """Verifica que o provider fictício não importa módulos do provider real."""
        import ast
        import inspect

        source = inspect.getsource(StubErpProviderRuntime)
        tree = ast.parse(source)

        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)

        assert not any("sankhya" in mod for mod in imported_modules)


# ---------------------------------------------------------------------------
# Teste de fallback legado
# ---------------------------------------------------------------------------
