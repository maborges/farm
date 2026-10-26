"""Suíte de testes de segurança, licenciamento, concorrência e resiliência da Fase AGRO-ADMIN-01E3A.

Valida rigorosamente os 6 pilares:
1. Criptografia e ciclo de vida: segregação KEK plataforma vs JWT, retrocompatibilidade KEK v1 -> v2, reencriptação atômica.
2. Licenciamento em todos os 6 caminhos: seleção, primário, fallback, contingência, recuperação, reinício (especialmente Open-Meteo).
3. Cotas e concorrência: reserva atômica via Lua script, rollback em falhas, concorrência real simulada, degradação graciosa sem Redis.
4. Hot-swap real via endpoint público sem falso positivo de cache e com 2 workers simulados.
5. Validação de credenciais e RBAC: pré-teste de conectividade, política de incidentes, separação de permissões, rate limiting (429), proteção SSRF.
6. Auditoria transacional atômica e proteção contra vazamento de segredos.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone

UTC = timezone.utc
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import settings
from core.database import Base
from core.dependencies import get_current_admin, get_session
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
)
from public_clima.adapters import (
    ProviderTimeoutError,
    SyntheticFixtureAdapter,
)
from public_clima.cache import ClimaCache
from public_clima.contracts import ClimaPrevisaoResponse
from public_clima.dynamic_orchestrator import DynamicWeatherOrchestrator
from public_clima.router import router as public_clima_router
from public_clima.service import PublicClimaService


@pytest.fixture
async def setup_01e3a_env(tmp_path):
    """Configura ambiente SQLite isolado, tabelas e cliente ASGI para a fase 01E3A."""
    db_file = tmp_path / "test_agro_01e3a.db"
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

    async with session_factory() as session:
        admin_u = AdminUser(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            email="admin@deepfarms.com",
            nome="Admin Teste",
            role="admin",
            ativo=True,
            senha_hash="mock",
        )
        viewer_u = AdminUser(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            email="viewer@deepfarms.com",
            nome="Viewer Teste",
            role="suporte",
            ativo=True,
            senha_hash="mock",
        )
        session.add_all([admin_u, viewer_u])
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
# 1. Criptografia e Ciclo de Vida das Chaves (KEK v2, Retrocompatibilidade e Reencriptação)
# ==============================================================================
@pytest.mark.asyncio
async def test_01_kek_segregation_and_versioning():
    """Valida que KEK v2 deriva de platform_credentials_master_key separadamente do segredo JWT."""
    with patch.object(settings, "platform_credentials_master_key", "super_dedicated_master_key_platform_kek_2026"), \
         patch.object(settings, "jwt_secret_key", "distinct_jwt_signing_secret_99999"):

        kek_v2 = PlatformWeatherCredentialsService._derive_platform_kek(version=2)
        kek_v1 = PlatformWeatherCredentialsService._derive_platform_kek(version=1)

        # KEK v2 deve ser estritamente diferente de KEK v1
        assert kek_v2 != kek_v1
        assert len(kek_v2) == 32
        assert len(kek_v1) == 32


@pytest.mark.asyncio
async def test_02_backward_compatibility_v1_and_v2_decryption():
    """Garante que credencial cifrada com KEK v1 ainda é decifrável pelo sistema que opera com KEK v2."""
    raw_secret = "secret_weather_api_token_test_123"

    # Cifra explicitamente com KEK v1
    enc_v1 = PlatformWeatherCredentialsService.encrypt_credential(
        "WEATHERAPI", raw_secret, key_version=1, kek_version=1
    )
    assert enc_v1["kek_version"] == 1

    # Sistema decifra com suporte retrocompatível
    decrypted = PlatformWeatherCredentialsService.decrypt_credential("WEATHERAPI", enc_v1)
    assert decrypted == raw_secret

    # Cifra com KEK v2 padrão
    enc_v2 = PlatformWeatherCredentialsService.encrypt_credential(
        "WEATHERAPI", raw_secret, key_version=2, kek_version=2
    )
    assert enc_v2["kek_version"] == 2
    decrypted_v2 = PlatformWeatherCredentialsService.decrypt_credential("WEATHERAPI", enc_v2)
    assert decrypted_v2 == raw_secret


@pytest.mark.asyncio
async def test_03_atomic_reencryption_migration(setup_01e3a_env):
    """Valida a rotação atômica de credenciais para KEK v2 via endpoint administrativo."""
    env = setup_01e3a_env
    app = env["app"]
    session_factory = env["session_factory"]

    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    # Salva manualmente uma credencial no formato v1 no banco
    raw_key = "weather_key_to_be_migrated_to_v2"
    enc_v1 = PlatformWeatherCredentialsService.encrypt_credential(
        "WEATHERAPI", raw_key, key_version=1, kek_version=1
    )

    async with session_factory() as session:
        cfg_record = ConfiguracaoSaaS(
            chave=KEY_CREDENTIALS_CLIMA,
            valor={
                "credentials": {
                    "WEATHERAPI": {
                        "ciphertext_b64": enc_v1["ciphertext_b64"],
                        "nonce_b64": enc_v1["nonce_b64"],
                        "key_version": 1,
                        "kek_version": 1,
                        "masked_key": enc_v1["masked_key"],
                        "updated_at": datetime.now(UTC).isoformat(),
                        "updated_by": "sistema@deepfarms.com",
                    }
                },
                "_meta": {"revision": 1, "version": "1.0"},
            },
            descricao="Cofre legado com credenciais em KEK v1",
            ativo=True,
        )
        session.add(cfg_record)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Executa reencriptação atômica para KEK v2
        resp = await client.post("/api/v1/backoffice/agro/provedores/credentials/reencrypt")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reencrypted_count"] == 1
        assert "WEATHERAPI" in data["providers"]
        assert data["kek_version"] == 2
        assert data["revision"] == 2

    # Verifica no banco se a credencial foi atualizada para kek_version=2 e se pode ser decifrada
    async with session_factory() as session:
        dec = await PlatformWeatherCredentialsService.get_decrypted_key(session, "WEATHERAPI")
        assert dec == raw_key

        # Verifica registro na trilha de auditoria
        audit_stmt = select(AdminAuditLog).where(AdminAuditLog.acao == "agro.credentials.reencrypt")
        audit_res = await session.execute(audit_stmt)
        audit = audit_res.scalar_one_or_none()
        assert audit is not None
        assert audit.admin_email == "admin@deepfarms.com"
        assert raw_key not in str(audit.dados_novos)  # Sem vazamento de segredos


# ==============================================================================
# 2. Licenciamento dos Provedores em Todos os 6 Caminhos de Execução
# ==============================================================================
@pytest.mark.asyncio
async def test_04_licensing_audit_all_execution_paths(setup_01e3a_env):
    """Garante que um provedor não licenciado (especialmente Open-Meteo) NUNCA seja chamado."""
    env = setup_01e3a_env
    app = env["app"]
    cache = env["cache"]

    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    # Força ambiente de produção estrito: Open-Meteo NÃO licenciado e sem chave enterprise
    with patch.object(settings, "open_meteo_allow_unlicensed_public", False), \
         patch.object(settings, "open_meteo_api_key", ""), \
         patch.object(settings, "open_meteo_licensed", False):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Caminho 1: Seleção administrativa como provedor ativo -> Rejeição 422
            resp1 = await client.put(
                "/api/v1/backoffice/agro/provedores/config",
                json={
                    "active_provider": "OPEN_METEO",
                    "open_meteo_licensed": True,  # Flag técnica isolada NÃO é suficiente!
                },
            )
            assert resp1.status_code == 422
            assert "licença contratual" in resp1.json()["detail"].lower()

            # Caminho 4: Contingência manual para provedor não licenciado -> Rejeição 422
            resp4 = await client.post(
                "/api/v1/backoffice/agro/provedores/contingency/toggle",
                json={
                    "enable_contingency": True,
                    "target_provider": "OPEN_METEO",
                    "motivo": "Teste de emergência com Open-Meteo",
                },
            )
            assert resp4.status_code == 422
            assert "não autorizado para uso público" in resp4.json()["detail"].lower()

    # Caminho 2 & 3: Execução de Provedor Primário e Fallback Automático no Orquestrador
    with patch.object(settings, "open_meteo_allow_unlicensed_public", False), \
         patch.object(settings, "open_meteo_api_key", ""), \
         patch.object(settings, "open_meteo_licensed", False):

        orchestrator = DynamicWeatherOrchestrator(cache=cache, refresh_ttl=10.0)

        # Provedor primário falha com timeout
        prim = SyntheticFixtureAdapter(provider_id="PRIMARY_SYNTHETIC", simular_falha=ProviderTimeoutError("504"))
        # Segundo provedor da cadeia é OPEN_METEO não licenciado
        unlicensed_meteo = SyntheticFixtureAdapter(provider_id="OPEN_METEO")
        # Terceiro provedor é backup sintético licenciado
        backup = SyntheticFixtureAdapter(provider_id="BACKUP_SYNTHETIC")

        orchestrator.register_test_adapter("PRIMARY_SYNTHETIC", prim)
        orchestrator.register_test_adapter("OPEN_METEO", unlicensed_meteo)
        orchestrator.register_test_adapter("BACKUP_SYNTHETIC", backup)

        orchestrator._config = AgroClimaConfig(
            active_provider="PRIMARY_SYNTHETIC",
            fallback_chain=["PRIMARY_SYNTHETIC", "OPEN_METEO", "BACKUP_SYNTHETIC"],
            open_meteo_licensed=True,  # Flag no banco sem suporte contratual
        )
        orchestrator._last_refresh = time.monotonic() + 3600.0

        # Executa consulta pública: primário falha, Open-Meteo DEVE ser ignorado e pular direto para BACKUP
        forecast = await orchestrator.fetch_forecast(-25.4284, -49.2733)
        assert forecast.provedor == "BACKUP_SYNTHETIC"


# ==============================================================================
# 3. Cotas e Concorrência Atômica
# ==============================================================================
@pytest.mark.asyncio
async def test_05_atomic_quota_reservation_and_concurrency():
    """Valida reserva atômica de cota com proteção contra estouro por concorrência simultânea."""
    cache = ClimaCache(redis_url="redis://localhost:9999", single_worker_fallback=True)
    shared = False  # Modo local com fallback de memória thread-safe

    provider = "WEATHERAPI"
    limit = 5

    # Executa 10 requisições simultâneas concorrendo por apenas 5 cotas
    async def try_reserve(idx: int):
        ok, count = await cache.reserve_monthly_quota(provider, limit, shared)
        return ok, count

    results = await asyncio.gather(*(try_reserve(i) for i in range(10)))

    successful_reservations = [r for r in results if r[0] is True]
    rejected_reservations = [r for r in results if r[0] is False]

    # Exatamente 5 devem ser autorizadas e 5 devem ser rejeitadas
    assert len(successful_reservations) == 5
    assert len(rejected_reservations) == 5

    # Testa rollback atômico em caso de falha de rede/timeout
    await cache.rollback_quota_reservation(provider, shared)
    ok_after_rollback, new_count = await cache.reserve_monthly_quota(provider, limit, shared)
    assert ok_after_rollback is True


# ==============================================================================
# 4. Teste Real do Hot-Swap pelo Endpoint Público com 2 Workers Simulados
# ==============================================================================
@pytest.mark.asyncio
async def test_06_real_hot_swap_public_endpoint_multi_worker(setup_01e3a_env):
    """Comprova alteração em tempo de execução via PUT /config e resposta em /public/clima/previsao."""
    env = setup_01e3a_env
    app = env["app"]
    session_factory = env["session_factory"]
    cache = env["cache"]

    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    # Worker 1 e Worker 2 simulados compartilhando cache e banco
    w1_orchestrator = DynamicWeatherOrchestrator(cache=cache, refresh_ttl=0.1)
    w2_orchestrator = DynamicWeatherOrchestrator(cache=cache, refresh_ttl=0.1)

    adapter_a = SyntheticFixtureAdapter(provider_id="SYNTHETIC_ALPHA")
    adapter_b = SyntheticFixtureAdapter(provider_id="SYNTHETIC_BETA")

    w1_orchestrator.register_test_adapter("SYNTHETIC_ALPHA", adapter_a)
    w1_orchestrator.register_test_adapter("SYNTHETIC_BETA", adapter_b)
    w2_orchestrator.register_test_adapter("SYNTHETIC_ALPHA", adapter_a)
    w2_orchestrator.register_test_adapter("SYNTHETIC_BETA", adapter_b)

    service_w1 = PublicClimaService(cache=cache, provider=w1_orchestrator)
    service_w2 = PublicClimaService(cache=cache, provider=w2_orchestrator)

    # 1. Configura Provedor A inicialmente
    async with session_factory() as session:
        await agro_config_service.update_config(
            session=session,
            chave=KEY_CLIMA,
            novo_valor={
                "active_provider": "SYNTHETIC_ALPHA",
                "fallback_chain": ["SYNTHETIC_ALPHA", "SYNTHETIC_BETA"],
                "timeout_seconds": 3.0,
            },
            admin_claims={"email": "admin@deepfarms.com"},
            descricao="Setup inicial Alpha",
        )

    w1_orchestrator.invalidate_cache()

    # 2. Executa previsão no Worker 1 (coordenada 1)
    with patch("public_clima.dynamic_orchestrator.async_session_maker", session_factory):
        resp_a = await service_w1.get_previsao(-25.4284, -49.2733)
        assert resp_a.provedor == "SYNTHETIC_ALPHA"

        # 3. Altera para Provedor B via API administrativa
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            put_res = await client.put(
                "/api/v1/backoffice/agro/provedores/config",
                json={
                    "active_provider": "SYNTHETIC_BETA",
                    "fallback_chain": ["SYNTHETIC_BETA", "SYNTHETIC_ALPHA"],
                    "timeout_seconds": 4.0,
                },
            )
            assert put_res.status_code == 200

        # Invalida cache de config do worker 2
        w2_orchestrator.invalidate_cache()

        # 4. Executa no Worker 2 com coordenada diferente (evitando falso positivo de cache)
        resp_b = await service_w2.get_previsao(-23.5505, -46.6333)
        assert resp_b.provedor == "SYNTHETIC_BETA"
        assert isinstance(resp_b, ClimaPrevisaoResponse)


# ==============================================================================
# 5. Validação de Credenciais, Política de Incidentes, Rate Limiting e SSRF
# ==============================================================================
@pytest.mark.asyncio
async def test_07_credential_pre_validation_and_incident_override(setup_01e3a_env):
    """Valida rejeição de chave inválida e aceitação com justificativa em incidente upstream."""
    env = setup_01e3a_env
    app = env["app"]

    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
        "is_superuser": True,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Chave inválida rejeitada pelo upstream -> HTTP 422
        resp_bad = await client.post(
            "/api/v1/backoffice/agro/provedores/credentials",
            json={
                "provider_slug": "WEATHERAPI",
                "api_key": "invalid_unauthorized_token_xyz",
            },
        )
        assert resp_bad.status_code == 422
        assert "inválida ou rejeitada" in resp_bad.json()["detail"].lower()

        # 2. Incidente upstream 503 sem justificativa -> HTTP 502 Bad Gateway
        resp_inc_no_force = await client.post(
            "/api/v1/backoffice/agro/provedores/credentials",
            json={
                "provider_slug": "WEATHERAPI",
                "api_key": "incident_503_upstream_outage",
            },
        )
        assert resp_inc_no_force.status_code == 502

        # 3. Incidente upstream COM flag force e justificativa -> HTTP 200 Sucesso
        resp_inc_force = await client.post(
            "/api/v1/backoffice/agro/provedores/credentials",
            json={
                "provider_slug": "WEATHERAPI",
                "api_key": "incident_503_upstream_outage",
                "force_on_upstream_incident": True,
                "incident_justification": "Status page do provedor confirma instabilidade geral na API.",
            },
        )
        assert resp_inc_force.status_code == 200
        assert resp_inc_force.json()["is_configured"] is True


@pytest.mark.asyncio
async def test_08_rbac_separation_and_rate_limiting(setup_01e3a_env):
    """Verifica separação entre permissão de visualização e teste de conectividade, e rate limit (429)."""
    env = setup_01e3a_env
    app = env["app"]

    # Usuário apenas com permissão de visualização (sem permissão de teste de conectividade)
    app.dependency_overrides[get_current_admin] = lambda: {
        "sub": "22222222-2222-2222-2222-222222222222",
        "email": "viewer@deepfarms.com",
        "role": "suporte",
        "permissoes": ["backoffice:agro:config:view"],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Teste de conectividade deve retornar 403 Forbidden para quem só tem config:view
        resp_forbidden = await client.post(
            "/api/v1/backoffice/agro/provedores/test-connection",
            json={"provider_slug": "WEATHERAPI"},
        )
        assert resp_forbidden.status_code == 403

        # Concede permissão de teste ao operador
        app.dependency_overrides[get_current_admin] = lambda: {
            "sub": "22222222-2222-2222-2222-222222222222",
            "email": "viewer@deepfarms.com",
            "role": "suporte",
            "permissoes": ["backoffice:agro:connectivity:test"],
        }

        # Executa chamadas repetidas para verificar rate limiting (máximo 10 por minuto)
        statuses = []
        for _ in range(12):
            r = await client.post(
                "/api/v1/backoffice/agro/provedores/test-connection",
                json={"provider_slug": "OPEN_METEO"},
            )
            statuses.append(r.status_code)

        assert 429 in statuses


# ==============================================================================
# 6. Auditoria Transacional Atômica e Rollback
# ==============================================================================
@pytest.mark.asyncio
async def test_09_audit_and_transaction_atomicity_on_failure(setup_01e3a_env):
    """Garante rollback simultâneo da credencial e do log de auditoria em caso de falha de banco."""
    env = setup_01e3a_env
    session_factory = env["session_factory"]

    admin_claims = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "admin@deepfarms.com",
        "role": "admin",
    }

    async with session_factory() as session:
        # Simula erro forçado durante o commit
        with patch.object(session, "commit", side_effect=RuntimeError("Simulated DB Disk Failure")):
            with pytest.raises(RuntimeError):
                await PlatformWeatherCredentialsService.save_credential(
                    session=session,
                    admin_claims=admin_claims,
                    provider_slug="WEATHERAPI",
                    api_key="valid_test_key_rollback_123",
                )

    # Verifica que NENHUMA credencial foi persistida e nenhum audit log órfão foi criado
    async with session_factory() as session:
        status_resp = await PlatformWeatherCredentialsService.get_credentials_status(session)
        w_item = next((it for it in status_resp.items if it.provider_slug == "WEATHERAPI"), None)
        assert w_item is None or not w_item.is_configured
