"""PostgreSQL integration regression tests, restricted to the RLS lab."""

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from core.database import (
    DB_URL as APP_DATABASE_URL,
    async_session_maker as app_session_factory,
    engine as app_engine,
)
from core.dependencies import _activate_session_tenant


LAB_URL = os.getenv("DEEPFARMS_RLS_LAB_DATABASE_URL")


@pytest_asyncio.fixture
async def lab_session_factory():
    if not LAB_URL:
        pytest.skip("DEEPFARMS_RLS_LAB_DATABASE_URL não configurada")

    url = make_url(LAB_URL)
    assert url.host == "192.168.0.2", "RLS integration tests só aceitam o host autorizado"
    assert url.port == 5432, "RLS integration tests só aceitam a porta autorizada"
    assert url.database == "deepfarms_rls_lab", "RLS integration tests só aceitam o banco de laboratório"
    assert url.username == "deepfarms_rls_lab_runtime", "RLS integration tests exigem a role runtime"

    app_url = make_url(APP_DATABASE_URL)
    assert (app_url.host, app_url.port, app_url.database, app_url.username) == (
        url.host,
        url.port,
        url.database,
        url.username,
    ), "core.database precisa estar inicializado diretamente para o laboratório"
    async with app_engine.connect() as connection:
        identity = (
            await connection.execute(
                text("SELECT current_database(), current_user, session_user")
            )
        ).one()
        assert tuple(identity) == (
            "deepfarms_rls_lab",
            "deepfarms_rls_lab_runtime",
            "deepfarms_rls_lab_runtime",
        )
    try:
        yield app_session_factory
    finally:
        await app_engine.dispose()


async def _current_tenant(session):
    return await session.scalar(
        text("SELECT NULLIF(current_setting('app.current_tenant_id', true), '')")
    )


async def _visible_tenants(session):
    return set(
        (await session.execute(text("SELECT DISTINCT tenant_id::text FROM farms.rls_probe")))
        .scalars()
        .all()
    )


@pytest.mark.asyncio
async def test_rls_session_isolation_and_reapplication_after_commit_rollback_error(lab_session_factory):
    factory = lab_session_factory
    async with factory() as session:
        assert await _current_tenant(session) is None
        assert await _visible_tenants(session) == set()

        await _activate_session_tenant(session, "tenant-a")
        assert await _current_tenant(session) == "tenant-a"
        assert await _visible_tenants(session) == {"tenant-a"}
        await session.commit()

        # A nova transação é iniciada pelo SELECT: after_begin reaplica A.
        assert await _current_tenant(session) == "tenant-a"
        assert await _visible_tenants(session) == {"tenant-a"}
        await session.rollback()

        assert await _current_tenant(session) == "tenant-a"
        assert await _visible_tenants(session) == {"tenant-a"}
        await session.commit()

        # A mesma Session pode mudar para B; a nova transação recebe somente B.
        await _activate_session_tenant(session, "tenant-b")
        assert await _current_tenant(session) == "tenant-b"
        assert await _visible_tenants(session) == {"tenant-b"}
        await session.rollback()

        with pytest.raises(DBAPIError):
            await session.execute(text("SELECT 1 / 0"))
        await session.rollback()
        assert await _current_tenant(session) == "tenant-b"
        assert await _visible_tenants(session) == {"tenant-b"}

    # Uma Session pública/sem Tenant continua neutra no backend reutilizado.
    async with factory() as session:
        assert await _current_tenant(session) is None
        assert await _visible_tenants(session) == set()


@pytest.mark.asyncio
async def test_rls_session_commit_rollback_and_pool_reuse(lab_session_factory):
    factory = lab_session_factory
    committed_marker = f"01g_commit_{uuid.uuid4()}"
    rolled_back_marker = f"01g_rollback_{uuid.uuid4()}"
    backend_ids = []

    try:
        async with factory() as session:
            session.info["tenant_id"] = "tenant-a"
            backend_ids.append(await session.scalar(text("SELECT pg_backend_pid()")))
            await session.execute(
                text("INSERT INTO farms.rls_probe (tenant_id, dado) VALUES ('tenant-a', :marker)"),
                {"marker": committed_marker},
            )
            await session.commit()

        async with factory() as session:
            session.info["tenant_id"] = "tenant-a"
            backend_ids.append(await session.scalar(text("SELECT pg_backend_pid()")))
            committed = await session.scalar(
                text("SELECT count(*) FROM farms.rls_probe WHERE dado = :marker"),
                {"marker": committed_marker},
            )
            assert committed == 1
            await session.execute(
                text("INSERT INTO farms.rls_probe (tenant_id, dado) VALUES ('tenant-a', :marker)"),
                {"marker": rolled_back_marker},
            )
            await session.rollback()

        async with factory() as session:
            session.info["tenant_id"] = "tenant-a"
            backend_ids.append(await session.scalar(text("SELECT pg_backend_pid()")))
            rolled_back = await session.scalar(
                text("SELECT count(*) FROM farms.rls_probe WHERE dado = :marker"),
                {"marker": rolled_back_marker},
            )
            assert rolled_back == 0
            await session.rollback()

        assert len(set(backend_ids)) == 1
    finally:
        async with factory() as session:
            session.info["tenant_id"] = "tenant-a"
            await session.execute(
                text("DELETE FROM farms.rls_probe WHERE dado IN (:committed, :rolled_back)"),
                {"committed": committed_marker, "rolled_back": rolled_back_marker},
            )
            await session.commit()
