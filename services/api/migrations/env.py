import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from core.database import DB_URL, Base
from core.model_registry import register_models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# O registry é a única fonte de carregamento dos models ORM do Alembic.
register_models()
target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", DB_URL.replace("%", "%%"))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """Exclude the known legacy constraint not safe for autogenerate."""
    if type_ == "unique_constraint" and name == "uq_produto_tenant_codigo_interno":
        return False
    return True


def _ensure_alembic_version_capacity(connection: Connection) -> None:
    if "postgresql" not in DB_URL:
        return
    row = connection.execute(
        text(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'farms'
              AND table_name = 'alembic_version'
              AND column_name = 'version_num'
            """
        )
    ).scalar_one_or_none()
    if row is not None and row < 64:
        connection.execute(
            text(
                "ALTER TABLE farms.alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(64)"
            )
        )


def do_run_migrations(connection: Connection) -> None:
    if "postgresql" in DB_URL:
        connection.execute(text("SET search_path TO farms"))
        _ensure_alembic_version_capacity(connection)
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(DB_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
