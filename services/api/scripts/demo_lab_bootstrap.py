"""Prepare only the empty demonstration database with the canonical clean install.

Run from services/api after provisioning the dedicated owner/runtime roles.
This script does not create demonstration business data or start workers.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.demo_lab_guard import DemoLabTargetError, validate_demo_lab_url

API_ROOT = Path(__file__).resolve().parents[1]


def lab_url() -> str:
    """Use only the existing development connection credentials and isolated database."""
    value = dotenv_values(API_ROOT / ".env.local", interpolate=False).get("DATABASE_URL")
    if not value:
        raise DemoLabTargetError("Development connection configuration is unavailable")
    target = make_url(value).set(database="deepfarms_demo_lab")
    url = target.render_as_string(hide_password=False)
    validate_demo_lab_url(url)
    return url


async def verify_empty_owner(connection) -> None:
    """Verify database identity and empty state before any schema modification."""
    identity = (await connection.execute(text("""
        SELECT current_database(), current_user, session_user,
               pg_get_userbyid(d.datdba), r.rolsuper, r.rolbypassrls
        FROM pg_database d JOIN pg_roles r ON r.rolname = current_user
        WHERE d.datname = current_database()
    """))).one()
    if tuple(identity) != (
        "deepfarms_demo_lab", "deepfarms_demo_owner", "borgus",
        "deepfarms_demo_owner", False, False,
    ):
        raise DemoLabTargetError("Connected database or owner identity is unexpected")
    occupied = (await connection.execute(text("""
        SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname NOT LIKE 'pg_toast%'
          AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
    """))).scalar_one()
    if occupied:
        raise DemoLabTargetError("Demonstration database is not empty")


def install_on_connection(connection) -> None:
    """Apply the canonical clean-install revision on the validated connection."""
    config = Config(str(API_ROOT / "migrations/clean_install/alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "migrations/clean_install"))
    config.attributes["connection"] = connection
    command.upgrade(config, "deepfarms_clean_install_v1")


async def main() -> None:
    """Install schema and grant runtime access in one isolated transaction."""
    url = lab_url()
    # The Alembic environment reads core.database.DB_URL; set it before importing it.
    os.environ["DATABASE_URL"] = url
    os.environ["RLS_DEV_ROUTE_SESSIONS_ENABLED"] = "false"
    os.environ["RLS_DEV_ALL_ROUTES_ENABLED"] = "false"
    os.environ["REQUIRE_RESTRICTED_RUNTIME_ROLE"] = "false"
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SET ROLE deepfarms_demo_owner"))
            await verify_empty_owner(connection)
            await connection.run_sync(install_on_connection)
            await connection.execute(text("GRANT USAGE ON SCHEMA farms TO deepfarms_demo_runtime"))
            await connection.execute(text(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA farms "
                "TO deepfarms_demo_runtime"
            ))
            await connection.execute(text(
                "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA farms TO deepfarms_demo_runtime"
            ))
    finally:
        await engine.dispose()
    print("Canonical clean install completed in deepfarms_demo_lab")


if __name__ == "__main__":
    asyncio.run(main())
