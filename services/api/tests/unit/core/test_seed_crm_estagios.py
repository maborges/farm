import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.models.crm import PipelineEstagio
from scripts.initial_load.seed_crm_estagios import (
    ESTAGIOS_PADRAO,
    seed_estagios_crm,
)


@pytest.mark.asyncio
async def test_crm_stage_seed_is_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection, tables=[PipelineEstagio.__table__]
            )
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            inserted = await seed_estagios_crm(session)
            assert inserted == len(ESTAGIOS_PADRAO)

        async with session_factory() as session:
            inserted_again = await seed_estagios_crm(session)
            count = await session.scalar(
                select(func.count()).select_from(PipelineEstagio)
            )
            assert inserted_again == 0
            assert count == len(ESTAGIOS_PADRAO)
    finally:
        await engine.dispose()
