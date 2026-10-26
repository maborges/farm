"""Environment for the independent clean-install lineage."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "homologacao"))
from agro_lab_migration_guard import enforce_lab_migration_guard  # noqa: E402

config = context.config
from core.database import DB_URL  # noqa: E402

config.set_main_option("sqlalchemy.url", DB_URL.replace("%", "%%"))
enforce_lab_migration_guard(DB_URL, getattr(config, "cmd_opts", None), config)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="deepfarms_install_version",
        version_table_schema="farms",
    )
    with context.begin_transaction():
        context.execute("CREATE SCHEMA IF NOT EXISTS farms")
        context.run_migrations()


def do_run_migrations(connection) -> None:
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS farms"))
    # Serialize competing install attempts, then repeat the empty-database
    # check while holding the transaction lock before Alembic creates a version row.
    connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('deepfarms-clean-install-v1'))"))
    occupied = connection.execute(
        text("""
        SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms' AND c.relkind IN ('r','p','v','m','S','f')
    """)
    ).scalar_one()
    if occupied:
        raise RuntimeError(
            "Clean install recusada: schema farms não está vazio sob lock transacional."
        )
    context.configure(
        connection=connection,
        version_table="deepfarms_install_version",
        version_table_schema="farms",
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    supplied = config.attributes.get("connection")
    if supplied is not None:
        do_run_migrations(supplied)
        return
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
elif config.attributes.get("connection") is not None:
    # The approved runner supplies an externally managed transaction so the
    # snapshot, seeds, Alembic version row, and catalog checks commit atomically.
    do_run_migrations(config.attributes["connection"])
else:
    asyncio.run(run_migrations_online())
