from __future__ import annotations

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agricola.models.templates import PhaseTemplate, PhaseTemplateChecklistItem
from core.database import Base
from scripts.initial_load import seed_checklist_templates as seed_module


async def _create_test_database():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[PhaseTemplate.__table__, PhaseTemplateChecklistItem.__table__],
            )
        )
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _assert_templates_follow_seed_order(session):
    rows = (
        await session.execute(
            select(
                PhaseTemplate.fase,
                PhaseTemplate.cultura,
                PhaseTemplateChecklistItem.titulo,
                PhaseTemplateChecklistItem.ordem,
            )
            .join(PhaseTemplate)
            .where(
                PhaseTemplate.tenant_id.is_(None),
                PhaseTemplate.is_system_default.is_(True),
            )
        )
    ).all()
    actual = {}
    for fase, cultura, titulo, ordem in rows:
        actual.setdefault((fase, cultura), []).append((ordem, titulo))

    expected = {}
    for fase, cultura, titulo, _obrigatorio in seed_module.TEMPLATES:
        expected.setdefault((fase, cultura), []).append(titulo)

    assert set(actual) == set(expected)
    for group, expected_titles in expected.items():
        ordered_rows = sorted(actual[group])
        assert [ordem for ordem, _titulo in ordered_rows] == list(
            range(len(expected_titles))
        )
        assert [titulo for _ordem, titulo in ordered_rows] == expected_titles


@pytest.mark.asyncio
async def test_checklist_seed_inicializa_orm_eh_global_ordenado_e_idempotente(
    monkeypatch,
):
    from sqlalchemy.orm import configure_mappers

    from core import model_registry

    engine, session_factory = await _create_test_database()
    events = []
    register = model_registry.register_models
    configure = configure_mappers

    def register_and_record():
        events.append("register_models")
        register()

    def configure_and_record():
        events.append("configure_mappers")
        configure()

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def record_sql(*_args):
        events.append("query")

    monkeypatch.setattr(model_registry, "register_models", register_and_record)
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", configure_and_record)
    monkeypatch.setattr(seed_module, "async_session_maker", session_factory)

    try:
        await seed_module.seed()
        first_query = events.index("query")
        assert events.index("register_models") < events.index("configure_mappers")
        assert events.index("configure_mappers") < first_query

        async with session_factory() as session:
            item_count = await session.scalar(
                select(func.count()).select_from(PhaseTemplateChecklistItem)
            )
            template_count = await session.scalar(
                select(func.count())
                .select_from(PhaseTemplate)
                .where(
                    PhaseTemplate.tenant_id.is_(None),
                    PhaseTemplate.is_system_default.is_(True),
                )
            )
            assert item_count == len(seed_module.TEMPLATES) == 47
            assert template_count == len(
                {(fase, cultura) for fase, cultura, *_ in seed_module.TEMPLATES}
            ) == 14
            await _assert_templates_follow_seed_order(session)

        await seed_module.seed()
        async with session_factory() as session:
            item_count = await session.scalar(
                select(func.count()).select_from(PhaseTemplateChecklistItem)
            )
            assert item_count == len(seed_module.TEMPLATES)
            await _assert_templates_follow_seed_order(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_checklist_seed_completa_carga_parcial_e_corrige_ordem_existente(
    monkeypatch,
):
    from sqlalchemy.orm import configure_mappers

    from core.model_registry import register_models

    register_models()
    configure_mappers()
    engine, session_factory = await _create_test_database()
    fase, cultura, titulo, obrigatorio = seed_module.TEMPLATES[0]
    try:
        async with session_factory() as session:
            template = PhaseTemplate(
                tenant_id=None,
                cultura=cultura,
                fase=fase,
                titulo=f"Template {fase}",
                is_system_default=True,
                ativo=True,
            )
            session.add(template)
            await session.flush()
            session.add(
                PhaseTemplateChecklistItem(
                    phase_template_id=template.id,
                    titulo=titulo,
                    descricao=None,
                    obrigatorio=obrigatorio,
                    ordem=77,
                    ativo=True,
                )
            )
            await session.commit()

        monkeypatch.setattr(seed_module, "async_session_maker", session_factory)
        await seed_module.seed()
        async with session_factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(PhaseTemplateChecklistItem)
            )
            assert count == len(seed_module.TEMPLATES)
            await _assert_templates_follow_seed_order(session)

        await seed_module.seed()
        async with session_factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(PhaseTemplateChecklistItem)
            )
            assert count == len(seed_module.TEMPLATES)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_checklist_seed_faz_rollback_se_commit_falha(monkeypatch):
    engine, session_factory = await _create_test_database()
    rollback_calls = 0
    original_rollback = AsyncSession.rollback

    async def fail_commit(_session):
        raise RuntimeError("commit failure")

    async def record_rollback(session):
        nonlocal rollback_calls
        rollback_calls += 1
        await original_rollback(session)

    monkeypatch.setattr(seed_module, "async_session_maker", session_factory)
    monkeypatch.setattr(seed_module, "TEMPLATES", seed_module.TEMPLATES[:3])
    monkeypatch.setattr(AsyncSession, "commit", fail_commit)
    monkeypatch.setattr(AsyncSession, "rollback", record_rollback)

    try:
        with pytest.raises(RuntimeError, match="commit failure"):
            await seed_module.seed()

        assert rollback_calls >= 1
        async with session_factory() as session:
            assert await session.scalar(
                select(func.count()).select_from(PhaseTemplate)
            ) == 0
            assert await session.scalar(
                select(func.count()).select_from(PhaseTemplateChecklistItem)
            ) == 0
    finally:
        await engine.dispose()
