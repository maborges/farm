import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.cadastros.produtos.models import ProdutoCultura, SoloParametroCultura
from core.database import Base
from scripts.initial_load.seed_parametros_solo import (
    PARAMETROS,
    seed_parametros_solo,
)


@pytest.mark.asyncio
async def test_soil_parameters_seed_is_idempotent_and_updates_system_cultures():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[ProdutoCultura.__table__, SoloParametroCultura.__table__],
            )
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    expected_rows = sum(len(data["faixas"]) for data in PARAMETROS.values())
    try:
        async with session_factory() as session:
            session.add_all(
                [
                    ProdutoCultura(nome=name, sistema=True, tenant_id=None)
                    for name in PARAMETROS
                ]
            )
            await session.commit()
            created, skipped, missing = await seed_parametros_solo(session)
            assert (created, skipped, missing) == (expected_rows, 0, 0)

        async with session_factory() as session:
            created_again, skipped_again, missing_again = await seed_parametros_solo(session)
            row_count = await session.scalar(
                select(func.count()).select_from(SoloParametroCultura)
            )
            cultures = (await session.execute(select(ProdutoCultura))).scalars().all()

            assert (created_again, skipped_again, missing_again) == (0, expected_rows, 0)
            assert row_count == expected_rows
            assert {
                culture.nome: float(culture.v_meta_pct_padrao) for culture in cultures
            } == {
                name: data["v_meta_pct_padrao"] for name, data in PARAMETROS.items()
            }
    finally:
        await engine.dispose()
