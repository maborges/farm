"""Fixtures para testes de integridade referencial do schema farms."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.config import settings


def _db_url() -> str:
    url = str(settings.database_url)
    if "postgresql" not in url:
        return "postgresql+asyncpg://borgus:numsey01@192.168.0.2/farms"
    return url


@pytest.fixture(scope="session")
async def catalog_session() -> AsyncSession:
    """Sessão somente-leitura no schema farms para consultas ao catálogo PostgreSQL."""
    engine = create_async_engine(_db_url(), echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(text("SET search_path = farms, public"))
        yield session
    await engine.dispose()
