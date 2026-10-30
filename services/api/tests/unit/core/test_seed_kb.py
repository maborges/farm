import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.models.knowledge_base import ConhecimentoArtigo, ConhecimentoCategoria
from scripts.initial_load.seed_kb import KB_INICIAL, seed_kb_with_session


@pytest.mark.asyncio
async def test_knowledge_base_seed_is_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[ConhecimentoCategoria.__table__, ConhecimentoArtigo.__table__],
            )
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    expected_articles = sum(len(articles) for _, _, articles in KB_INICIAL.values())
    try:
        async with session_factory() as session:
            await seed_kb_with_session(session)

        async with session_factory() as session:
            await seed_kb_with_session(session)
            category_count = await session.scalar(
                select(func.count()).select_from(ConhecimentoCategoria)
            )
            article_count = await session.scalar(
                select(func.count()).select_from(ConhecimentoArtigo)
            )
            public_article_count = await session.scalar(
                select(func.count())
                .select_from(ConhecimentoArtigo)
                .where(ConhecimentoArtigo.is_publico.is_(True))
            )

            assert category_count == len(KB_INICIAL)
            assert article_count == expected_articles
            assert public_article_count == expected_articles
    finally:
        await engine.dispose()
