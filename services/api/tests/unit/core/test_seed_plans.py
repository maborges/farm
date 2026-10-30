import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.models.billing import PlanoAssinatura
from scripts.initial_load.seed_plans import (
    PLANOS_INICIAIS,
    seed_plans_with_session,
)


@pytest.mark.asyncio
async def test_plan_seed_is_active_snapshot_and_idempotent():
    assert all(plan["ativo"] for plan in PLANOS_INICIAIS)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection, tables=[PlanoAssinatura.__table__]
            )
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            inserted = await seed_plans_with_session(session)
            assert inserted == len(PLANOS_INICIAIS)

        async with session_factory() as session:
            inserted_again = await seed_plans_with_session(session)
            count = await session.scalar(select(func.count()).select_from(PlanoAssinatura))
            assert inserted_again == 0
            assert count == len(PLANOS_INICIAIS)
    finally:
        await engine.dispose()
