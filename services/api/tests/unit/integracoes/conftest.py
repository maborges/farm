import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

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
from integracoes.sankhya.models import SankhyaConfig, SankhyaNFe, SankhyaSyncLog


@pytest_asyncio.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: MarketplaceIntegracao.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: IntegrationCredential.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: TenantIntegracao.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: IntegrationVersion.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: SankhyaConfig.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: SankhyaSyncLog.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: IntegrationFeature.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: IntegrationSyncPolicy.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: IntegrationJob.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: IntegrationHealth.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: ExternalRecordAssociation.__table__.create(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: SankhyaNFe.__table__.create(sync_conn, checkfirst=True)
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as current:
        yield current

    await engine.dispose()
