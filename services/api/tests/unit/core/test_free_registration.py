"""Cadastro global gratuito em banco temporário, inclusive concorrência."""

import asyncio
import sqlite3

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.dependencies import get_session
from core.models.auth import Usuario
from core.routers.auth import router as auth_router
from core.schemas.auth_schemas import FreeUserCreateRequest
from core.services.auth_service import AuthService
from core.services.free_registration_rate_limit import FreeRegistrationRateLimiter
from scripts.diagnosticar_migracao_identidade_agro import build_report, inspect_sqlite


import os
from core.database import Base


def _create_engine_for_test(tmp_path, name: str):
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    is_ci = os.getenv("CI_POSTGRESQL") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    if db_url and "postgresql" in db_url:
        return create_async_engine(db_url, connect_args={"server_settings": {"search_path": "farms,public"}})
    if is_ci:
        raise RuntimeError("CI detectada mas TEST_DATABASE_URL não configurado.")
    return create_async_engine(f"sqlite+aiosqlite:///{tmp_path / name}")


@pytest.mark.asyncio
async def test_cadastro_gratuito_concorrente_cria_um_usuario(tmp_path):
    engine = _create_engine_for_test(tmp_path, "identity-test.db")
    async with engine.begin() as connection:
        if "postgresql" in str(engine.url):
            from sqlalchemy import text
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS farms"))
            await connection.execute(text("SET search_path TO farms, public"))
            await connection.execute(text("DELETE FROM farms.usuarios WHERE email = 'produtora@example.com'"))
        await connection.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[Usuario.__table__]))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    payload = FreeUserCreateRequest(
        nome="Produtora Teste",
        email="PRODUTORA@example.com",
        senha="SenhaSegura@123",
    )

    async def register_once():
        async with session_factory() as session:
            return await AuthService(session).register_free_user(payload)

    results = await asyncio.gather(*(register_once() for _ in range(6)))
    assert sum(created for _, created in results) == 1

    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(Usuario))
        user = (await session.execute(select(Usuario))).scalar_one()
    assert count == 1
    assert user.email == "produtora@example.com"
    assert user.cpf is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_colisao_de_username_recebe_sufixo_sem_alterar_email(tmp_path):
    engine = _create_engine_for_test(tmp_path, "username-collision.db")
    async with engine.begin() as connection:
        if "postgresql" in str(engine.url):
            from sqlalchemy import text
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS farms"))
            await connection.execute(text("SET search_path TO farms, public"))
            await connection.execute(text("DELETE FROM farms.usuarios WHERE email IN ('pessoa@example.com', 'pessoa@example.org')"))
        await connection.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[Usuario.__table__]))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        first, first_created = await AuthService(session).register_free_user(
            FreeUserCreateRequest(
                nome="Pessoa Um",
                email="pessoa@example.com",
                senha="SenhaSegura@123",
            )
        )
    async with session_factory() as session:
        second, second_created = await AuthService(session).register_free_user(
            FreeUserCreateRequest(
                nome="Pessoa Dois",
                email="pessoa@example.org",
                senha="SenhaSegura@456",
            )
        )

    assert first_created and second_created
    assert first is not None and second is not None
    assert first.username == "pessoa"
    assert second.username.startswith("pessoa_")
    assert first.username != second.username
    await engine.dispose()


@pytest.mark.asyncio
async def test_endpoint_cadastro_nao_enumera_email_existente(tmp_path):
    engine = _create_engine_for_test(tmp_path, "identity-http.db")
    async with engine.begin() as connection:
        if "postgresql" in str(engine.url):
            from sqlalchemy import text
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS farms"))
            await connection.execute(text("SET search_path TO farms, public"))
            await connection.execute(text("DELETE FROM farms.usuarios WHERE email = 'pessoa@example.com'"))
        await connection.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[Usuario.__table__]))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def isolated_session():
        async with session_factory() as session:
            yield session

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[get_session] = isolated_session
    await FreeRegistrationRateLimiter.reset_for_tests()

    payload = {
        "nome": "Pessoa Teste",
        "email": "pessoa@example.com",
        "senha": "SenhaSegura@123",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        created = await client.post("/api/v1/auth/register-free", json=payload)
        duplicate = await client.post("/api/v1/auth/register-free", json=payload)

    assert created.status_code == duplicate.status_code == 202
    assert created.json() == duplicate.json()
    assert "email" not in created.text.lower()
    assert created.headers.get("set-cookie") is None
    assert duplicate.headers.get("set-cookie") is None
    assert created.headers["content-type"] == duplicate.headers["content-type"]
    await engine.dispose()


def test_diagnostico_migracao_e_somente_leitura_e_detecta_dependencias(tmp_path):
    database_path = tmp_path / "agro-identity.db"
    db = sqlite3.connect(database_path)
    db.executescript(
        """
        CREATE TABLE agro_usuarios (
          id TEXT, email TEXT, senha_hash TEXT, ativo INTEGER, email_verificado INTEGER
        );
        CREATE TABLE agro_sessoes (id TEXT);
        CREATE TABLE agro_tokens_recuperacao (id TEXT);
        CREATE TABLE agro_tokens_verificacao (id TEXT);
        CREATE TABLE agro_user_byok_credentials (id TEXT);
        INSERT INTO agro_usuarios VALUES (
          '11111111-1111-1111-1111-111111111111',
          'Pessoa@Example.com', '$2b$12$hash', 1, 1
        );
        INSERT INTO agro_user_byok_credentials VALUES ('byok-1');
        """
    )
    db.commit()
    db.close()

    summary, source = inspect_sqlite(database_path)
    report = build_report(
        summary,
        source,
        [{"id": "22222222-2222-2222-2222-222222222222", "email": "pessoa@example.com"}],
    )
    assert report["mode"] == "DRY_RUN_READ_ONLY"
    assert report["collisions"]["email_count"] == 1
    assert report["summary"]["source_byok_credentials"] == 1
    assert report["migration_rules"]["byok_requires_same_uuid_or_controlled_decrypt_and_reencrypt"]
