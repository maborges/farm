"""Repositório de dados segregado para identidades individuais do DeepFarms Agro.

Garante pool de conexões próprio e isolamento absoluto do banco comercial PostgreSQL (db_pool_size=3).
"""

from __future__ import annotations

import os
from typing import AsyncGenerator
from loguru import logger
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .config import AGRO_IDENTITY_DB_URL, ensure_secure_storage

# Engine assíncrona dedicada exclusivamente para identidades individuais do Agro
agro_identity_engine = create_async_engine(
    AGRO_IDENTITY_DB_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in AGRO_IDENTITY_DB_URL else {},
)

if "sqlite" in AGRO_IDENTITY_DB_URL:
    @event.listens_for(agro_identity_engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
        # Assegura que novos arquivos criados pelo SQLite (WAL e SHM) tenham permissões restritas
        ensure_secure_storage()

agro_async_session_maker = async_sessionmaker(
    bind=agro_identity_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

AgroBase = declarative_base()


async def get_agro_db() -> AsyncGenerator[AsyncSession, None]:
    """Injeta sessão assíncrona do banco segregado de identidades do Agro."""
    async with agro_async_session_maker() as session:
        yield session


async def init_agro_db() -> None:
    """Cria tabelas do repositório segregado se não existirem e executa migrações versionadas com umask restrito."""
    from . import models  # noqa: F401 - garante registro dos models na metadata
    from .migrations import run_agro_migrations

    old_umask = os.umask(0o077)
    try:
        ensure_secure_storage()
        # 1. Executa migrações versionadas do banco Agro
        run_agro_migrations()
        # 2. Assegura sincronização dos models ORM
        async with agro_identity_engine.begin() as conn:
            await conn.run_sync(AgroBase.metadata.create_all)
        ensure_secure_storage()
    finally:
        os.umask(old_umask)

    logger.info("Repositório segregado de identidades individuais do Agro inicializado e versionado.")


async def close_agro_db() -> None:
    """Libera o pool de conexões do repositório de identidades do Agro no encerramento."""
    await agro_identity_engine.dispose()
    logger.info("Engine de identidades do Agro encerrada.")
