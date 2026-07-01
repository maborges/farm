# ruff: noqa: S105, S106
from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import Column, Table
from sqlalchemy import Uuid as UUIDType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import Base
from integracoes.models import (
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
from integracoes.sankhya.services.sync_service import (
    SankhyaConfigSerializer,
    SankhyaSyncService,
)
from integracoes.security import decrypt_integration_secret, is_integration_secret_encrypted

REPO_ROOT = Path(__file__).resolve().parents[5]
SANKHYA_ROUTERS = REPO_ROOT / "services/api/integracoes/sankhya/routers/__init__.py"
SANKHYA_MODELS = REPO_ROOT / "services/api/integracoes/sankhya/models/__init__.py"
TENANT_SIDEBAR = REPO_ROOT / "apps/web/src/components/layout/app-sidebar.tsx"
BACKOFFICE_PAGE = (
    REPO_ROOT / "apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx"
)
PERMISSIONS_TS = REPO_ROOT / "apps/web/src/lib/permissions.ts"

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


@pytest.mark.asyncio
async def test_senha_e_persistida_protegida(session: AsyncSession) -> None:
    service = SankhyaSyncService(session)
    config = await service.criar_config(
        tenant_id="tenant-1",
        ws_url="https://erp.example/ws",
        username="usuario",
        password="senha-original",
        sync_interval=900,
    )

    assert config.password != "senha-original"
    assert is_integration_secret_encrypted(config.password)
    assert decrypt_integration_secret(config.password) == "senha-original"


@pytest.mark.asyncio
async def test_resposta_nao_retorna_senha_bruta(session: AsyncSession) -> None:
    service = SankhyaSyncService(session)
    config = await service.criar_config(
        tenant_id="tenant-1",
        ws_url="https://erp.example/ws",
        username="usuario",
        password="segredo",
        sync_interval=900,
    )

    payload = SankhyaConfigSerializer.to_response(config)

    assert "password" not in payload
    assert payload["password_configured"] is True
    assert payload["password_mask"] == "••••••••"


@pytest.mark.asyncio
async def test_atualizacao_sem_nova_senha_mantem_credencial_existente(
    session: AsyncSession,
) -> None:
    service = SankhyaSyncService(session)
    config = await service.criar_config(
        tenant_id="tenant-1",
        ws_url="https://erp.example/ws",
        username="usuario",
        password="segredo-inicial",
        sync_interval=900,
    )
    encrypted = config.password

    updated = await service.atualizar_config(
        config,
        ws_url="https://erp.example/ws/v2",
        username="usuario-2",
        password=None,
        sync_interval=1200,
    )

    assert updated.password == encrypted
    assert decrypt_integration_secret(updated.password) == "segredo-inicial"


@pytest.mark.asyncio
async def test_rotacao_de_senha_funciona(session: AsyncSession) -> None:
    service = SankhyaSyncService(session)
    config = await service.criar_config(
        tenant_id="tenant-1",
        ws_url="https://erp.example/ws",
        username="usuario",
        password="senha-antiga",
        sync_interval=900,
    )
    previous_password = config.password

    rotated = await service.atualizar_config(
        config,
        ws_url="https://erp.example/ws",
        username="usuario",
        password="senha-nova",
        sync_interval=900,
    )

    assert decrypt_integration_secret(rotated.password) == "senha-nova"
    assert rotated.password != previous_password


def test_rotas_usam_sessao_compativel_com_rls() -> None:
    routers = SANKHYA_ROUTERS.read_text(encoding="utf-8")

    assert "Depends(get_session)" in routers
    assert "Depends(get_db)" not in routers
    assert "Depends(get_tenant_id)" in routers


def test_permissoes_de_tenant_nao_dependem_de_backoffice() -> None:
    sidebar = TENANT_SIDEBAR.read_text(encoding="utf-8")
    permissions = PERMISSIONS_TS.read_text(encoding="utf-8")

    assert 'href: "/dashboard/settings/integracoes/erp"' in sidebar
    assert 'permission: "integrations:view"' in sidebar
    assert '"integrations:view"' in permissions
    assert '"backoffice:integrations:observe"' in permissions


def test_backoffice_nao_e_console_principal_da_configuracao() -> None:
    backoffice_page = BACKOFFICE_PAGE.read_text(encoding="utf-8")

    assert "console primário de configuração" in backoffice_page
    assert "/dashboard/settings/integracoes/erp" in backoffice_page
    assert "Jobs canônicos" in backoffice_page


def test_sankhya_permanece_tenant_scoped_sem_unidade_produtiva() -> None:
    models = SANKHYA_MODELS.read_text(encoding="utf-8")
    routers = SANKHYA_ROUTERS.read_text(encoding="utf-8")

    assert "tenant_id = Column(String(50), nullable=False, unique=True, index=True)" in models
    assert "unidade_produtiva_id" not in models
    assert "unidade_produtiva_id" not in routers


def test_rotas_expoem_status_health_e_jobs_sem_quebrar_logs_legados() -> None:
    routers = SANKHYA_ROUTERS.read_text(encoding="utf-8")

    assert '"/status"' in routers
    assert '"/health"' in routers
    assert '"/jobs"' in routers
    assert '"/logs"' in routers
    assert '"/timeline"' in routers
    assert '"/diagnostico"' in routers
