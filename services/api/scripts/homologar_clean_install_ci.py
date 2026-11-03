#!/usr/bin/env python3
"""Homologate the canonical clean-install revision on GitHub's disposable PostgreSQL."""

from __future__ import annotations

import asyncio
import os
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from clean_install import INSTALL_VERSION

API_ROOT = Path(__file__).resolve().parents[1]
CLEAN_INSTALL_ROOT = API_ROOT / "migrations" / "clean_install"
EXPECTED_DATABASE = "farms_test"
EXPECTED_USER = "deepfarms_test"
EXPECTED_HOST = "localhost"
EXPECTED_PORT = 5432


def _validated_ci_database_url(environ: Mapping[str, str]) -> str:
    """Accept only the temporary PostgreSQL service configured by the CI workflow."""
    if environ.get("GITHUB_ACTIONS", "").lower() != "true":
        raise RuntimeError("Clean-install CI homologation requires the GitHub Actions runner.")
    if environ.get("CI_POSTGRESQL", "").lower() != "true":
        raise RuntimeError("Clean-install CI homologation requires CI_POSTGRESQL=true.")

    database_url = environ.get("DATABASE_URL", "")
    test_database_url = environ.get("TEST_DATABASE_URL", "")
    if not database_url or database_url != test_database_url:
        raise RuntimeError(
            "DATABASE_URL and TEST_DATABASE_URL must match the disposable CI target."
        )

    try:
        target = make_url(database_url)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("CI PostgreSQL target URL is invalid.") from exc

    if (
        target.drivername != "postgresql+asyncpg"
        or target.host != EXPECTED_HOST
        or target.port != EXPECTED_PORT
        or target.database != EXPECTED_DATABASE
        or target.username != EXPECTED_USER
        or not target.password
    ):
        raise RuntimeError("CI PostgreSQL target does not match the disposable service identity.")
    return database_url


async def _assert_empty_target(engine) -> None:
    async with engine.connect() as connection:
        identity = (
            await connection.execute(
                text("SELECT current_database(), session_user, inet_server_port()")
            )
        ).one()
        if identity != (EXPECTED_DATABASE, EXPECTED_USER, EXPECTED_PORT):
            raise RuntimeError(
                "Connected PostgreSQL identity differs from the disposable CI target."
            )

        schema_exists = (
            await connection.execute(text("SELECT to_regnamespace('farms') IS NOT NULL"))
        ).scalar_one()
        application_objects = (
            await connection.execute(
                text("""
                    SELECT count(*) FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                      AND n.nspname NOT LIKE 'pg_toast%'
                      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
                """)
            )
        ).scalar_one()
        versions = (
            await connection.execute(
                text("""
                    SELECT to_regclass('farms.deepfarms_install_version'),
                           to_regclass('farms.alembic_version')
                """)
            )
        ).one()

        if schema_exists or application_objects or any(versions):
            raise RuntimeError("Disposable CI database is not empty; clean install refused.")


def _clean_install_config(database_url: str) -> Config:
    config = Config(str(CLEAN_INSTALL_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(CLEAN_INSTALL_ROOT))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


async def _validate_installed_catalog(engine) -> dict[str, int]:
    from sqlalchemy import MetaData, Table, func, select

    from clean_install.catalog_validation import validate_catalog
    from clean_install.manifest import verify_artifact_hashes
    from clean_install.seed_contract import SEEDS

    hashes = verify_artifact_hashes(API_ROOT)
    expected_seed_counts = Counter(row.table for row in SEEDS)
    async with engine.connect() as connection:
        catalog = await connection.run_sync(
            lambda sync_connection: validate_catalog(
                sync_connection, expected_manifest=hashes, check_version=True
            )
        )
        legacy_version_table = (
            await connection.execute(text("SELECT to_regclass('farms.alembic_version')"))
        ).scalar_one_or_none()
        if legacy_version_table is not None:
            raise RuntimeError("Historical Alembic version table exists in clean-install database.")

        def read_seed_counts(sync_connection) -> dict[str, int]:
            metadata = MetaData()
            observed_counts: dict[str, int] = {}
            for table_name, expected_count in sorted(expected_seed_counts.items()):
                seed_table = Table(
                    table_name, metadata, schema="farms", autoload_with=sync_connection
                )
                observed = sync_connection.execute(
                    select(func.count()).select_from(seed_table)
                ).scalar_one()
                if observed != expected_count:
                    raise RuntimeError(f"Clean-install seed row count mismatch for {table_name}.")
                observed_counts[table_name] = observed
            return observed_counts

        observed_seed_counts = await connection.run_sync(read_seed_counts)

    return catalog | {"seed_catalog_rows": sum(observed_seed_counts.values())}


async def main() -> None:
    database_url = _validated_ci_database_url(os.environ)

    # Verify core.database resolves the same runner-provided target before Alembic imports env.py.
    from core.database import DB_URL

    if make_url(DB_URL) != make_url(database_url):
        raise RuntimeError("Application settings resolve a different database target than CI.")

    engine = create_async_engine(
        database_url,
        connect_args={"server_settings": {"search_path": "farms,public"}},
    )
    try:
        await _assert_empty_target(engine)
        config = _clean_install_config(database_url)
        # Run only the independent canonical install revision, never historical upgrades/downgrades.
        await asyncio.to_thread(command.upgrade, config, INSTALL_VERSION)
        catalog = await _validate_installed_catalog(engine)
    finally:
        await engine.dispose()

    print(
        f"Clean install homologated: {INSTALL_VERSION}; "
        f"database={EXPECTED_DATABASE}; catalog={catalog}"
    )


if __name__ == "__main__":
    asyncio.run(main())
