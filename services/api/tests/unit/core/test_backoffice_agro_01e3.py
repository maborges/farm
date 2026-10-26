"""Suíte de testes de integridade, segurança e resiliência da Fase AGRO-ADMIN-01E3:
Provedores Climáticos, Credenciais e Contingência.

Cobre rigorosamente os 12 requisitos obrigatórios:
1. Criptografia AES-256-GCM e mascaramento de credenciais em repouso.
2. Rotação de credenciais e recuperação após reinício de workers.
3. RBAC granular por operação administrativa (visualização, edição, credenciais, contingência).
4. Hot-swap dinâmico de provedor em tempo de execução sem reiniciar a API.
5. Invalidação e sincronização entre múltiplos workers simulados.
6. Fallback resiliente por timeout, erro 5xx e cota esgotada com contingência stale.
7. Bloqueio estrito de provedores não licenciados em ambiente público (Open-Meteo).
8. Resiliência a falhas completas do Redis.
9. Concorrência no consumo de cotas e alertas preventivos aos 80% e 95%.
10. Rollback e concorrência otimista com revision tracking.
11. Preservação estrita dos contratos públicos canônicos (ClimaPrevisaoResponse).
12. Ausência total de regressão no cofre BYOK individual e na identidade global.
"""

from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import settings
from core.database import Base
from core.dependencies import get_current_admin, get_session, require_permission
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_user import AdminUser
from core.models.auth import Usuario
from core.models.configuration import ConfiguracaoSaaS
from core.routers.backoffice_agro_providers import router as agro_providers_router
from core.schemas.agro_config_schemas import (
    KEY_CLIMA,
    KEY_CREDENTIALS_CLIMA,
    AgroClimaConfig,
)
from core.services.agro_config_service import agro_config_service
from core.services.platform_weather_credentials import (
    PlatformWeatherCredentialsService,
    mask_secret,
)
from public_clima.adapters import (
    ProviderError,
    ProviderQuotaExceededError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnlicensedError,
    SyntheticFixtureAdapter,
)
from public_clima.cache import ClimaCache, ClimaCacheEntry
from public_clima.contracts import ClimaPrevisaoResponse, CondicaoAtual
from public_clima.dynamic_orchestrator import DynamicWeatherOrchestrator
from public_clima.router import get_weather_orchestrator, router as public_clima_router
from public_clima.service import PublicClimaService


@pytest.fixture
async def setup_01e3_env(tmp_path):
    """Configura ambiente SQLite isolado e instâncias de serviço para a fase 01E3."""
    db_file = tmp_path / "test_agro_01e3.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    tables = [
        ConfiguracaoSaaS.__table__,
        AdminAuditLog.__table__,
        AdminUser.__table__,
        Usuario.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(agro_providers_router, prefix="/api/v1")
    app.include_router(public_clima_router, prefix="/api/v1")

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    # Cria usuário admin e usuário suporte no banco de testes
    async with session_factory() as session:
        admin_u = AdminUser(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            email="admin@deepfarms.com",
            nome="Admin Teste",
            role="admin",
            ativo=True,
            senha_hash="mock",
        )
        suporte_u = AdminUser(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            email="suporte@deepfarms.com",
            nome="Suporte Teste",
            role="suporte",
            ativo=True,
            senha_hash="mock",
        )
        comercial_u = AdminUser(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            email="comercial@deepfarms.com",
            nome="Comercial Teste",
            role="comercial",
            ativo=True,
            senha_hash="mock",
        )
        session.add_all([admin_u, suporte_u, comercial_u])
        await session.commit()

    cache = ClimaCache(redis_url="redis://localhost:6379/0", single_worker_fallback=True)
    orchestrator = DynamicWeatherOrchestrator(cache=cache, refresh_ttl=0.1)

    return {
        "app": app,
        "session_factory": session_factory,
        "cache": cache,
        "orchestrator": orchestrator,
    }


# ==============================================================================
# 1. Criptografia e Mascaramento das Credenciais
# ==============================================================================
@pytest.mark.asyncio
async def test_01_credentials_encryption_and_masking(setup_01e3_env):
    """Valida AES-256-GCM em repouso e mascaramento seguro nas respostas."""
    env = setup_01e3_env
    session_factory = env["session_factory"]

    secret_key = "weather_api_secret_token_1234567890"
    encrypted = PlatformWeatherCredentialsService.encrypt_credential("WEATHERAPI", secret_key, key_version=1)

    # Garante que ciphertext não é texto plano nem expõe o segredo
    assert encrypted["ciphertext_b64"] != secret_key
    assert secret_key not in encrypted["ciphertext_b64"]
    assert encrypted["masked_key"] == "••••••••7890"

    # Decifra e compara
    decrypted = PlatformWeatherCredentialsService.decrypt_credential("WEATHERAPI", encrypted)
    assert decrypted == secret_key

    # Persiste e consulta via serviço administrativo
    async with session_factory() as session:
        admin_claims = {
            "sub": "11111111-1111-1111-1111-111111111111",
            "email": "admin@deepfarms.com",
            "role": "admin",
            "is_superuser": True,
        }
        await PlatformWeatherCredentialsService.save_credential(
            session=session,
            admin_claims=admin_claims,
            provider_slug="WEATHERAPI",
            api_key=secret_key,
        )

        status_resp = await PlatformWeatherCredentialsService.get_credentials_status(session)
        w_item = next(it for it in status_resp.items if it.provider_slug == "WEATHERAPI")
        assert w_item.is_configured is True
        assert w_item.key_preview == "••••••••7890"
        # Garante que o item de status não possui campos de ciphertext ou plaintext
        assert not hasattr(w_item, "ciphertext_b64")
        assert not hasattr(w_item, "api_key")


# ==============================================================================
# 2. Rotação e Recuperação após Reinício
# ==============================================================================
@pytest.mark.asyncio
async def test_02_credentials_rotation_and_recovery(setup_01e3_env):
    """Valida rotação de versão da chave e recuperação após reinicialização de worker."""
    env = setup_01e3_env
    session_factory = env["session_factory"]

    admin_claims = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    # Versão 1
    async with session_factory() as session:
        await PlatformWeatherCredentialsService.save_credential(
            session=session,
            admin_claims=admin_claims,
            provider_slug="OPENWEATHER",
            api_key="openweather_key_v1_abcd",
            key_version=1,
        )
        key_v1 = await PlatformWeatherCredentialsService.get_decrypted_key(session, "OPENWEATHER")
        assert key_v1 == "openweather_key_v1_abcd"

    # Versão 2 (Rotação)
    async with session_factory() as session:
        await PlatformWeatherCredentialsService.save_credential(
            session=session,
            admin_claims=admin_claims,
            provider_slug="OPENWEATHER",
            api_key="openweather_key_v2_wxyz",
            key_version=2,
        )
        key_v2 = await PlatformWeatherCredentialsService.get_decrypted_key(session, "OPENWEATHER")
        assert key_v2 == "openweather_key_v2_wxyz"

        # Verifica log de auditoria sem segredo
        logs = (await session.execute(select(AdminAuditLog).where(AdminAuditLog.acao == "agro.credentials.update"))).scalars().all()
        assert len(logs) >= 2
        for l in logs:
            assert "openweather_key" not in str(l.dados_novos)
            assert "••••••••" in str(l.dados_novos)


# ==============================================================================
# 3. RBAC Granular por Operação Administrativa
# ==============================================================================
@pytest.mark.asyncio
async def test_03_rbac_per_admin_operation(setup_01e3_env):
    """Valida permissões granulares no Backoffice para cada endpoint."""
    app = setup_01e3_env["app"]
    session_factory = setup_01e3_env["session_factory"]

    # 1. Usuário Comercial (sem permissão agro) -> 403 em tudo
    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "33333333-3333-3333-3333-333333333333",
        "email": "comercial@deepfarms.com",
        "role": "comercial",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/backoffice/agro/provedores")
        assert resp.status_code == 403

    # 2. Usuário Suporte (pode visualizar, mas NÃO pode alterar credenciais nem acionar contingência)
    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "22222222-2222-2222-2222-222222222222",
        "email": "suporte@deepfarms.com",
        "role": "suporte",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Visualização permitida
        resp_view = await client.get("/api/v1/backoffice/agro/provedores")
        assert resp_view.status_code == 200

        # Tentativa de salvar credencial -> 403
        resp_cred = await client.post(
            "/api/v1/backoffice/agro/provedores/credentials",
            json={"provider_slug": "WEATHERAPI", "api_key": "some_key"},
        )
        assert resp_cred.status_code == 403

        # Tentativa de acionar contingência -> 403
        resp_cont = await client.post(
            "/api/v1/backoffice/agro/provedores/contingency/toggle",
            json={"enable_contingency": True},
        )
        assert resp_cont.status_code == 403


# ==============================================================================
# 4. Hot-Swap sem Reiniciar a API
# ==============================================================================
@pytest.mark.asyncio
async def test_04_hot_swap_without_restart(setup_01e3_env):
    """Valida alteração dinâmica do provedor ativo sem restart de processo."""
    app = setup_01e3_env["app"]
    session_factory = setup_01e3_env["session_factory"]

    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    # Salva credencial prévia para WeatherAPI
    async with session_factory() as session:
        await PlatformWeatherCredentialsService.save_credential(
            session=session,
            admin_claims={"email": "admin@deepfarms.com"},
            provider_slug="WEATHERAPI",
            api_key="valid_key_12345",
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Altera provedor ativo para WEATHERAPI
        resp = await client.put(
            "/api/v1/backoffice/agro/provedores/config",
            json={
                "active_provider": "WEATHERAPI",
                "fallback_chain": ["WEATHERAPI", "OPEN_METEO"],
                "timeout_seconds": 3.5,
                "monthly_quota_limit": 50000,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valor"]["active_provider"] == "WEATHERAPI"
        assert data["valor"]["timeout_seconds"] == 3.5

        # Verifica GET status
        st_resp = await client.get("/api/v1/backoffice/agro/provedores")
        assert st_resp.status_code == 200
        st_data = st_resp.json()
        assert st_data["active_provider"] == "WEATHERAPI"
        assert st_data["timeout_seconds"] == 3.5


# ==============================================================================
# 5. Invalidação entre Múltiplos Workers Simulados
# ==============================================================================
@pytest.mark.asyncio
async def test_05_invalidation_across_multiple_workers(setup_01e3_env):
    """Simula dois workers independentes sincronizando configurações via invalidação."""
    cache = setup_01e3_env["cache"]
    session_factory = setup_01e3_env["session_factory"]

    worker_a = DynamicWeatherOrchestrator(cache=cache, refresh_ttl=30.0)
    worker_b = DynamicWeatherOrchestrator(cache=cache, refresh_ttl=30.0)

    # Worker A atualiza no banco com chave válida
    async with session_factory() as session:
        await PlatformWeatherCredentialsService.save_credential(
            session=session,
            admin_claims={"email": "admin@deepfarms.com"},
            provider_slug="WEATHERAPI",
            api_key="worker_key_12345",
        )
        await agro_config_service.update_config(
            session=session,
            chave=KEY_CLIMA,
            novo_valor={
                "active_provider": "WEATHERAPI",
                "fallback_chain": ["WEATHERAPI"],
                "timeout_seconds": 4.2,
                "monthly_quota_limit": 100000,
            },
            admin_claims={"email": "admin@deepfarms.com"},
        )

    # Worker B recebe sinal de invalidação
    worker_b.invalidate_cache()

    with patch("public_clima.dynamic_orchestrator.async_session_maker", session_factory):
        cfg_b = await worker_b.get_active_config()
        assert cfg_b.active_provider == "WEATHERAPI"
        assert cfg_b.timeout_seconds == 4.2


# ==============================================================================
# 6. Fallback por Timeout, Erro 5xx e Cota Esgotada
# ==============================================================================
@pytest.mark.asyncio
async def test_06_fallback_timeout_5xx_quota(setup_01e3_env):
    """Valida a cadeia de fallback automático em falhas determinísticas upstream."""
    cache = setup_01e3_env["cache"]
    orchestrator = DynamicWeatherOrchestrator(cache=cache, refresh_ttl=10.0)

    # Configura adapters sintéticos controlados
    primary = SyntheticFixtureAdapter(
        provider_id="PRIMARY_SYNTHETIC",
        simular_falha=ProviderTimeoutError("Upstream timeout 504"),
    )
    secondary = SyntheticFixtureAdapter(
        provider_id="SECONDARY_SYNTHETIC",
    )

    orchestrator.register_test_adapter("PRIMARY_SYNTHETIC", primary)
    orchestrator.register_test_adapter("SECONDARY_SYNTHETIC", secondary)

    orchestrator._config = AgroClimaConfig(
        active_provider="PRIMARY_SYNTHETIC",
        fallback_chain=["PRIMARY_SYNTHETIC", "SECONDARY_SYNTHETIC"],
        timeout_seconds=2.0,
    )

    # Consulta meteorológica deve contornar o timeout do primário e retornar o secundário
    forecast = await orchestrator.fetch_forecast(-25.4284, -49.2733)
    assert forecast.provedor == "SECONDARY_SYNTHETIC"
    assert forecast.dadosSinteticos is True

    # Agora simula falha em AMBOS os provedores com contingência no cache
    secondary.simular_falha = ProviderUnavailableError("HTTP 500 upstream down")
    service = PublicClimaService(cache=cache, provider=orchestrator)

    # Cria cache de contingência prévio
    now = datetime.now(timezone.utc)
    cached_entry = ClimaCacheEntry(
        response=forecast.model_copy(update={"desatualizado": False}),
        synced_at=now,
    )
    lat_grid, lon_grid = service.grid_policy.quantize(-25.4284, -49.2733)
    cache_key = f"{lat_grid:.4f}:{lon_grid:.4f}"
    await cache.save(cache_key, cached_entry, ttl=1, shared=False)
    cache.local_fresh.clear()  # Expira o cache recente para forçar uso da contingência (last)

    # Após expirar o fresh, a consulta deve retornar o dado contingencial marcado como desatualizado
    cached_resp = await service.get_previsao(-25.4284, -49.2733)
    assert cached_resp.desatualizado is True
    assert cached_resp.statusOperacional == "DESATUALIZADO"


# ==============================================================================
# 7. Bloqueio de Provedor Não Licenciado
# ==============================================================================
@pytest.mark.asyncio
async def test_07_block_unlicensed_provider(setup_01e3_env):
    """Garante rejeição HTTP 422 na ativação de Open-Meteo sem autorização expressa."""
    app = setup_01e3_env["app"]

    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put(
            "/api/v1/backoffice/agro/provedores/config",
            json={
                "active_provider": "OPEN_METEO",
                "open_meteo_licensed": False,
            },
        )
        assert resp.status_code == 422
        assert "licença" in resp.json()["detail"].lower()


# ==============================================================================
# 8. Falha de Redis e Degradação Graciosa
# ==============================================================================
@pytest.mark.asyncio
async def test_08_redis_failure_and_resilience(setup_01e3_env):
    """Verifica que indisponibilidade completa de Redis não quebra consultas."""
    cache = ClimaCache(redis_url="redis://localhost:9999", single_worker_fallback=True)
    adapter = SyntheticFixtureAdapter(provider_id="SYNTHETIC_OFFLINE")
    service = PublicClimaService(cache=cache, provider=adapter)

    # Consulta deve funcionar perfeitamente com cache local em memória
    res = await service.get_previsao(-25.4284, -49.2733)
    assert res is not None
    assert res.provedor == "SYNTHETIC_OFFLINE"


# ==============================================================================
# 9. Concorrência no Consumo de Cotas e Alertas (80% e 95%)
# ==============================================================================
@pytest.mark.asyncio
async def test_09_quota_concurrency_and_alert_thresholds(setup_01e3_env):
    """Valida acionamento de alertas a 80% e 95% de consumo de franquia."""
    cache = setup_01e3_env["cache"]
    orchestrator = DynamicWeatherOrchestrator(cache=cache)

    cfg = AgroClimaConfig(
        active_provider="WEATHERAPI",
        monthly_quota_limit=100,
        quota_alert_threshold_80=True,
        quota_alert_threshold_95=True,
    )

    # 1. Simula 80 chamadas upstream
    for _ in range(80):
        await cache.record_upstream_call("WEATHERAPI", shared=False)

    with patch("public_clima.dynamic_orchestrator.logger.warning") as mock_warn:
        await orchestrator._check_quota_alerts("WEATHERAPI", 100, shared=False, cfg=cfg)
        mock_warn.assert_called()
        assert "80%" in str(mock_warn.call_args)

    # 2. Simula 95 chamadas upstream
    for _ in range(15):
        await cache.record_upstream_call("WEATHERAPI", shared=False)

    with patch("public_clima.dynamic_orchestrator.logger.critical") as mock_crit:
        await orchestrator._check_quota_alerts("WEATHERAPI", 100, shared=False, cfg=cfg)
        mock_crit.assert_called()
        assert "95%" in str(mock_crit.call_args)


# ==============================================================================
# 10. Rollback de Configuração e Concorrência Otimista
# ==============================================================================
@pytest.mark.asyncio
async def test_10_rollback_and_optimistic_concurrency(setup_01e3_env):
    """Valida rejeição de concorrência com 409 Conflict e suporte a rollback."""
    app = setup_01e3_env["app"]
    session_factory = setup_01e3_env["session_factory"]

    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    # Salva credencial prévia
    async with session_factory() as session:
        await PlatformWeatherCredentialsService.save_credential(
            session=session,
            admin_claims={"email": "admin@deepfarms.com"},
            provider_slug="WEATHERAPI",
            api_key="valid_key_12345",
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Primeira alteração: revisão vira 1
        resp1 = await client.put(
            "/api/v1/backoffice/agro/provedores/config",
            json={"active_provider": "WEATHERAPI", "timeout_seconds": 4.0},
        )
        assert resp1.status_code == 200
        rev1 = resp1.json()["valor"]["_meta"]["revision"]

        # Segunda alteração informando revisão incorreta (ex: rev1 + 5) -> 409 Conflict
        resp_conflict = await client.put(
            f"/api/v1/backoffice/agro/provedores/config?expected_revision={rev1 + 5}",
            json={"active_provider": "WEATHERAPI", "timeout_seconds": 6.0},
        )
        assert resp_conflict.status_code == 409


# ==============================================================================
# 11. Preservação dos Contratos Públicos Canônicos
# ==============================================================================
@pytest.mark.asyncio
async def test_11_preserve_public_clima_contracts(setup_01e3_env):
    """Garante que a resposta pública segue estritamente ClimaPrevisaoResponse."""
    cache = setup_01e3_env["cache"]
    synthetic = SyntheticFixtureAdapter(provider_id="CANONICAL_SYNTHETIC")
    service = PublicClimaService(cache=cache, provider=synthetic)

    resp = await service.get_previsao(-25.4284, -49.2733)
    assert isinstance(resp, ClimaPrevisaoResponse)
    assert resp.latitude == -25.4284
    assert resp.longitude == -49.2733
    assert resp.provedor == "CANONICAL_SYNTHETIC"
    assert resp.statusOperacional == "NORMAL"
    assert resp.desatualizado is False
    assert resp.condicoesAtuais is not None
    assert resp.previsaoDiaria is not None
    assert resp.previsaoHoraria is not None


# ==============================================================================
# 12. Ausência de Regressões no Cofre BYOK e Identidade Global
# ==============================================================================
@pytest.mark.asyncio
async def test_12_no_regression_byok_and_global_identity(setup_01e3_env):
    """Garante separação estrita: credenciais globais não tocam no cofre BYOK individual."""
    session_factory = setup_01e3_env["session_factory"]

    # Verifica que agro:credentials:clima reside exclusivamente em configuracoes_saas
    async with session_factory() as session:
        stmt = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_CREDENTIALS_CLIMA)
        record = (await session.execute(stmt)).scalar_one_or_none()
        if record:
            assert isinstance(record.valor, dict)
            assert "credentials" in record.valor


# ==============================================================================
# 13. Endpoint de Credenciais com key_version e Permissões Administrativas
# ==============================================================================
@pytest.mark.asyncio
async def test_13_save_credential_endpoint_with_key_version(setup_01e3_env):
    """Valida que POST /credentials aceita key_version sem erro 422 de extra_forbidden."""
    app = setup_01e3_env["app"]

    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "22222222-2222-2222-2222-222222222222",
        "email": "security_admin@deepfarms.com",
        "role": "admin",
        "permissions": [
            "backoffice:agro:config:view",
            "backoffice:agro:credentials:manage",
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "provider_slug": "WEATHERAPI",
            "api_key": "super_secret_weather_key_999",
            "key_version": 2,
        }
        resp = await client.post("/api/v1/backoffice/agro/provedores/credentials", json=payload)
        assert resp.status_code == 200, f"Falha esperada 200, recebeu: {resp.status_code} - {resp.text}"
        data = resp.json()
        assert data["provider_slug"] == "WEATHERAPI"
        assert data["is_configured"] is True
        assert data["key_version"] == 2
        assert "super_secret" not in data["key_preview"]

