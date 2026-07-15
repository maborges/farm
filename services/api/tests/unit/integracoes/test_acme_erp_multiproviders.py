import uuid
from typing import Any
from types import SimpleNamespace
import pytest
from unittest.mock import AsyncMock

from integracoes.erp.provider_contract import ErpProviderRuntime
from integracoes.erp.provider_registry import ErpProviderRegistry
import integracoes.erp.router as erp_router_module

class _AcmeErpRuntime(ErpProviderRuntime):
    """Implementação fictícia de um segundo ERP (ACME) para testes."""
    
    @property
    def provider_slug(self) -> str:
        return "acme_erp"
        
    async def get_status(self, tenant_id: str) -> dict[str, Any]:
        return {"configurado": True, "provider": "ACME", "status": "ONLINE"}
        
    async def get_health(self, tenant_id: str) -> dict[str, Any]:
        return {"health": "OK", "latency": 15}
        
    async def get_jobs(self, tenant_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return [{"id": "acme-1", "status": "DONE"}]
        
    async def get_timeline(
        self, tenant_id: str, *, status: str | None = None,
        feature_code: str | None = None, origem: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        return []
        
    async def get_diagnosis(self, tenant_id: str) -> dict[str, Any]:
        return {"acme_diagnosis": "Perfect"}
        
    async def get_capabilities(self, tenant_id: str) -> list[dict[str, Any]]:
        return [{"feature": "billing"}]

def acme_factory(session: Any) -> ErpProviderRuntime:
    return _AcmeErpRuntime()

@pytest.mark.asyncio
async def test_acme_erp_provider_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    # 1. Configurar o Registry para conhecer o provedor "acme_erp"
    registry = ErpProviderRegistry()
    registry.register("acme_erp", acme_factory)
    monkeypatch.setattr(erp_router_module, "erp_provider_registry", registry)
    
    # 2. Simular que o ReadinessService carregou o TenantIntegracao apontando para "acme_erp"
    async def fake_carregar_runtime(self: object, implantacao: SimpleNamespace) -> SimpleNamespace:
        return SimpleNamespace(
            provider=SimpleNamespace(slug="acme_erp"),
            config=SimpleNamespace(id=999),
        )
    monkeypatch.setattr(erp_router_module.ErpReadinessService, "carregar_runtime", fake_carregar_runtime)
    
    readiness_service = erp_router_module.ErpReadinessService(session)
    
    # 3. Chamar as APIs genéricas (Router) e atestar que a resposta do ACME ERP sobe até a ponta
    status_response = await erp_router_module.obter_status_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )
    assert status_response == {"configurado": True, "provider": "ACME", "status": "ONLINE"}
    
    health_response = await erp_router_module.obter_health_erp(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=session,
    )
    assert health_response == {"health": "OK", "latency": 15}
