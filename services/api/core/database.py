from typing import AsyncGenerator
import os
import stat
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy import event, text
from sqlalchemy.engine import URL, make_url
from core.config import settings
from loguru import logger

# Criação da Engine Assíncrona para o PostgreSQL ou SQLite Fallback
DB_URL = str(settings.database_url)
if not DB_URL or "postgresql" not in DB_URL:
    if settings.require_restricted_runtime_role:
        raise ValueError(
            "DATABASE_URL must use PostgreSQL when REQUIRE_RESTRICTED_RUNTIME_ROLE is enabled"
        )
    DB_URL = "sqlite+aiosqlite:///./agrosaas.db"
    logger.warning("Usando banco local SQLite devido à falta de PostgreSQL configurado.")
else:
    # Corrige driver se não especificado ou se especificado asyncpg e ele não for achado
    try:
        import asyncpg
    except ImportError as exc:
        if settings.require_restricted_runtime_role:
            raise RuntimeError(
                "asyncpg is required when REQUIRE_RESTRICTED_RUNTIME_ROLE is enabled"
            ) from exc
        DB_URL = "sqlite+aiosqlite:///./agrosaas.db"
        logger.warning("asyncpg driver não encontrado. Usando banco local SQLite Fallback.")

engine = create_async_engine(
    DB_URL,
    echo=False,  # Em produção manter False para não floodar de logs SQL
    future=True,
    # Pool conservador: mantém baixa pressão em Postgres compartilhado.
    **({} if "sqlite" in DB_URL else {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_timeout": settings.db_pool_timeout,
    }),
    connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {
        "server_settings": {
            "search_path": "farms",
            # Evita conexões penduradas indefinidamente (idle em transação ou query travada).
            "options": "-c idle_in_transaction_session_timeout=30000 -c statement_timeout=60000",
        }
    }
)

# Development-only route integration: keep the legacy engine above untouched,
# but prepare dedicated restricted pools for the exact HTTP routes selected by
# core.dependencies.get_session(). Credentials are read from the same private
# file as the already-approved loopback canary and are never logged.
rls_dev_runtime_engine = None
rls_dev_async_session_maker = None
RLS_DEV_RUNTIME_DB_URL = ""
RLS_DEV_AUTH_DB_URL = ""
if settings.rls_dev_route_sessions_enabled:
    if settings.environment.lower() != "development":
        raise RuntimeError(
            "RLS_DEV_ROUTE_SESSIONS_ENABLED is allowed only in development"
        )
    if settings.require_restricted_runtime_role:
        raise RuntimeError(
            "Selective route mode requires REQUIRE_RESTRICTED_RUNTIME_ROLE=false "
            "so legacy endpoints keep their existing engine"
        )
    credentials_file = Path(os.environ.get(
        "DEEPFARMS_RLS_CANARY_ENV_FILE",
        Path(__file__).resolve().parent.parent / ".env.rls-canary.local",
    )).expanduser()
    if not credentials_file.is_file() or stat.S_IMODE(credentials_file.stat().st_mode) & 0o077:
        raise RuntimeError("Restricted route credentials file must exist with mode 0600")
    route_credentials = dotenv_values(credentials_file, interpolate=False)
    runtime_password = route_credentials.get("DEEPFARMS_CANARY_RUNTIME_PASSWORD")
    auth_password = route_credentials.get("DEEPFARMS_CANARY_AUTH_PASSWORD")
    if not runtime_password or not auth_password:
        raise RuntimeError("Restricted route credentials are incomplete")

    route_runtime_url = URL.create(
        "postgresql+asyncpg", username="deepfarms_runtime",
        password=runtime_password, host="192.168.0.2", port=5432, database="farms",
    )
    route_auth_url = URL.create(
        "postgresql+asyncpg", username="deepfarms_auth",
        password=auth_password, host="192.168.0.2", port=5432, database="farms",
    )
    RLS_DEV_RUNTIME_DB_URL = route_runtime_url.render_as_string(hide_password=False)
    RLS_DEV_AUTH_DB_URL = route_auth_url.render_as_string(hide_password=False)
    rls_dev_runtime_engine = create_async_engine(
        RLS_DEV_RUNTIME_DB_URL,
        echo=False,
        future=True,
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=settings.db_pool_timeout,
        connect_args={
            "server_settings": {
                "search_path": "farms",
                "application_name": "deepfarms-api-rls-dev-runtime",
                "options": "-c idle_in_transaction_session_timeout=30000 -c statement_timeout=60000",
            }
        },
    )

    @event.listens_for(rls_dev_runtime_engine.sync_engine, "connect")
    def _verify_dev_route_runtime_identity(dbapi_connection, connection_record):
        _configure_expected_restricted_connection(
            dbapi_connection, "deepfarms_runtime", "farms"
        )

    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker
        rls_dev_async_session_maker = async_sessionmaker(
            bind=rls_dev_runtime_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    except ImportError:
        rls_dev_async_session_maker = sessionmaker(
            bind=rls_dev_runtime_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )

# The recommendation dispatcher has a separate login and pool. When unset,
# no dispatcher factory is created; the scheduler fails closed instead of
# silently using the tenant runtime for cross-tenant discovery.
dispatcher_engine = None
dispatcher_async_session_maker = None
DISPATCHER_DB_URL = str(settings.recommendation_dispatcher_database_url or "").strip()
if DISPATCHER_DB_URL:
    if "postgresql" not in DISPATCHER_DB_URL:
        raise ValueError("RECOMMENDATION_DISPATCHER_DATABASE_URL must use PostgreSQL")
    dispatcher_engine = create_async_engine(
        DISPATCHER_DB_URL,
        echo=False,
        future=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=settings.db_pool_timeout,
        connect_args={
            "server_settings": {
                "search_path": "farms",
                "options": "-c idle_in_transaction_session_timeout=30000 -c statement_timeout=60000",
            }
        },
    )

# Dedicated connection pool for global catalog administration (Backoffice / seeds)
# when runtime operates under restricted tenant-only roles.
catalog_admin_engine = None
catalog_admin_async_session_maker = None
CATALOG_ADMIN_DB_URL = str(settings.catalog_admin_database_url or "").strip()
if CATALOG_ADMIN_DB_URL:
    if "postgresql" not in CATALOG_ADMIN_DB_URL:
        raise ValueError("CATALOG_ADMIN_DATABASE_URL must use PostgreSQL")
    catalog_admin_engine = create_async_engine(
        CATALOG_ADMIN_DB_URL,
        echo=False,
        future=True,
        pool_size=max(1, min(settings.db_pool_size, 2)),
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=settings.db_pool_timeout,
        connect_args={
            "server_settings": {
                "search_path": "farms",
                "options": "-c idle_in_transaction_session_timeout=30000 -c statement_timeout=60000",
            }
        },
    )

# Credential lookup has a dedicated pool and does not share the tenant runtime.
authentication_engine = None
authentication_async_session_maker = None
AUTHENTICATION_DB_URL = (
    RLS_DEV_AUTH_DB_URL
    or str(settings.authentication_database_url or "").strip()
)
if settings.require_restricted_runtime_role and not AUTHENTICATION_DB_URL:
    raise ValueError(
        "AUTHENTICATION_DATABASE_URL is required when REQUIRE_RESTRICTED_RUNTIME_ROLE is enabled"
    )
if AUTHENTICATION_DB_URL:
    auth_url = make_url(AUTHENTICATION_DB_URL)
    if auth_url.drivername not in {"postgresql+asyncpg", "postgresql"}:
        raise ValueError("AUTHENTICATION_DATABASE_URL must use PostgreSQL/asyncpg")
    if auth_url.username != settings.authentication_database_role:
        raise ValueError("AUTHENTICATION_DATABASE_URL username does not match AUTHENTICATION_DATABASE_ROLE")
    authentication_engine = create_async_engine(
        AUTHENTICATION_DB_URL,
        echo=False,
        future=True,
        pool_size=max(1, min(settings.db_pool_size, 2)),
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=settings.db_pool_timeout,
        connect_args={
            "server_settings": {
                "search_path": "farms,pg_catalog",
                **(
                    {"application_name": "deepfarms-api-rls-dev-auth"}
                    if settings.rls_dev_route_sessions_enabled else {}
                ),
                "options": "-c idle_in_transaction_session_timeout=10000 -c statement_timeout=10000",
            }
        },
    )

# Fábrica de Sessoes Assíncronas (compatível com SQLAlchemy 1.4 e 2.0)
try:
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
except ImportError:
    # Fallback para SQLAlchemy 1.4
    async_session_maker = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        future=True
    )

if dispatcher_engine is not None:
    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker

        dispatcher_async_session_maker = async_sessionmaker(
            bind=dispatcher_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    except ImportError:
        dispatcher_async_session_maker = sessionmaker(
            bind=dispatcher_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )

if authentication_engine is not None:
    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker

        authentication_async_session_maker = async_sessionmaker(
            bind=authentication_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    except ImportError:
        authentication_async_session_maker = sessionmaker(
            bind=authentication_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )

if catalog_admin_engine is not None:
    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker

        catalog_admin_async_session_maker = async_sessionmaker(
            bind=catalog_admin_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    except ImportError:
        catalog_admin_async_session_maker = sessionmaker(
            bind=catalog_admin_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )

# Base para os Models do ORM
Base = declarative_base()

# Reaplica o contexto autorizado em cada nova transação física da Session.
# O hook usa a Connection recebida pelo SQLAlchemy (não Session.execute), para
# não iniciar transações/consultas recursivas. Sessões sem tenant ficam neutras.
@event.listens_for(Session, "after_begin")
def apply_tenant_context_after_begin(session, transaction, connection):
    login_email = session.info.get("login_email")
    user_id = session.info.get("user_id")
    tenant_id = session.info.get("tenant_id")
    if connection.dialect.name != "postgresql":
        return

    if login_email is not None:
        connection.execute(
            text("SELECT set_config('app.current_login_email', :email, true)"),
            {"email": str(login_email)},
        )
    if user_id is not None:
        connection.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )
    if tenant_id is not None:
        connection.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )


# Configuração de isolamento por conexão; não instala contexto Tenant.
@event.listens_for(engine.sync_engine, "connect")
def set_tenant_context(dbapi_connection, connection_record):
    _configure_postgresql_connection(dbapi_connection, "postgresql" in DB_URL)


if dispatcher_engine is not None:
    event.listen(
        dispatcher_engine.sync_engine,
        "connect",
        lambda dbapi_connection, connection_record: _configure_postgresql_connection(
            dbapi_connection, "postgresql" in DISPATCHER_DB_URL
        ),
    )

if catalog_admin_engine is not None:
    event.listen(
        catalog_admin_engine.sync_engine,
        "connect",
        lambda dbapi_connection, connection_record: _configure_postgresql_connection(
            dbapi_connection, "postgresql" in CATALOG_ADMIN_DB_URL
        ),
    )


def _configure_postgresql_connection(dbapi_connection, is_postgresql: bool) -> None:
    """Apply connection safeguards to a PostgreSQL application identity."""
    if not is_postgresql:
        return
    if settings.require_restricted_runtime_role:
        _assert_restricted_database_role(dbapi_connection)
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(
            "SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED"
        )
    finally:
        cursor.close()


def _configure_authentication_connection(dbapi_connection, connection_record) -> None:
    """Enforce an isolated non-elevated login for credential lookup."""
    auth_url = make_url(AUTHENTICATION_DB_URL)
    _configure_expected_restricted_connection(
        dbapi_connection, auth_url.username, auth_url.database
    )


def _configure_expected_restricted_connection(
    dbapi_connection, expected_role: str, expected_database: str
) -> None:
    """Fail closed if a restricted pool authenticates as any other identity."""
    _assert_restricted_database_role(dbapi_connection)
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(
            "SELECT current_database(), current_user::text, session_user::text"
        )
        row = cursor.fetchone()
        if row != (expected_database, expected_role, expected_role):
            raise RuntimeError("Restricted route connection identity mismatch")
        cursor.execute(
            "SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED"
        )
    finally:
        cursor.close()


if authentication_engine is not None:
    event.listen(
        authentication_engine.sync_engine,
        "connect",
        _configure_authentication_connection,
    )


def _assert_restricted_database_role(dbapi_connection) -> None:
    """Reject elevated or owning identities when strict runtime mode is enabled."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(
            """
            WITH RECURSIVE role_memberships(role_oid) AS (
                SELECT am.roleid
                FROM pg_auth_members am
                JOIN pg_roles member_role ON member_role.oid = am.member
                WHERE member_role.rolname = session_user
                UNION
                SELECT am.roleid
                FROM pg_auth_members am
                JOIN role_memberships rm ON rm.role_oid = am.member
            )
            SELECT current_user::text,
                   session_user::text,
                   (r.rolsuper OR r.rolbypassrls OR r.rolcreatedb
                    OR r.rolcreaterole OR r.rolreplication),
                   EXISTS (SELECT 1 FROM role_memberships),
                   EXISTS (
                       SELECT 1
                       FROM pg_class c
                       JOIN pg_namespace n ON n.oid = c.relnamespace
                       WHERE n.nspname = 'farms'
                         AND c.relowner IN (
                             SELECT oid FROM pg_roles WHERE rolname = session_user
                             UNION SELECT role_oid FROM role_memberships
                         )
                   ),
                   EXISTS (
                       SELECT 1
                       FROM pg_namespace n
                       WHERE n.nspname = 'farms'
                         AND n.nspowner IN (
                             SELECT oid FROM pg_roles WHERE rolname = session_user
                             UNION SELECT role_oid FROM role_memberships
                         )
                   ),
                   EXISTS (
                       SELECT 1
                       FROM pg_database d
                       WHERE d.datname = current_database()
                         AND d.datdba IN (
                             SELECT oid FROM pg_roles WHERE rolname = session_user
                             UNION SELECT role_oid FROM role_memberships
                         )
                   )
            FROM pg_roles r
            WHERE r.rolname = current_user
            """
        )
        row = cursor.fetchone()
    finally:
        cursor.close()

    if row is None or row[0] != row[1] or any(row[2:]):
        raise RuntimeError(
            "Database connection must use a non-elevated runtime identity "
            "without memberships or ownership"
        )


# Dependência para injetar sessão do banco de dados (Dependency Injection)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependência do FastAPI para injetar sessão do banco de dados.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    db = async_session_maker()
    try:
        yield db
    finally:
        await db.close()


# Função utilitária para obter sessão única (para scripts e testes)
async def get_db_session() -> AsyncSession:
    """
    Obtém uma sessão única do banco de dados.
    
    Usage:
        db = await get_db_session()
        # ... usar db ...
        await db.close()
    """
    return async_session_maker()
