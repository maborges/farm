import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agricola.models.templates import PhaseTemplate, PhaseTemplateChecklistItem
from core.database import Base
from scripts.initial_load.seed_checklist_templates import (
    TEMPLATES,
    seed_checklist_templates,
)


@pytest.mark.asyncio
async def test_checklist_seed_is_global_and_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[PhaseTemplate.__table__, PhaseTemplateChecklistItem.__table__],
            )
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            inserted = await seed_checklist_templates(session)
            assert inserted == len(TEMPLATES)

        async with session_factory() as session:
            inserted_again = await seed_checklist_templates(session)
            assert inserted_again == 0

            item_count = await session.scalar(
                select(func.count()).select_from(PhaseTemplateChecklistItem)
            )
            global_system_count = await session.scalar(
                select(func.count())
                .select_from(PhaseTemplate)
                .where(
                    PhaseTemplate.tenant_id.is_(None),
                    PhaseTemplate.is_system_default.is_(True),
                )
            )
            assert item_count == len(TEMPLATES)
            assert global_system_count == len({(fase, cultura) for fase, cultura, *_ in TEMPLATES})
    finally:
        await engine.dispose()
