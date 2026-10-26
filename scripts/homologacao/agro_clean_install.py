#!/usr/bin/env python3
"""Fail-closed runner for the independent DeepFarms clean-install snapshot."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

API_ROOT = Path(__file__).resolve().parents[2] / "services" / "api"
REPO_ROOT = API_ROOT.parent.parent
# The runner is invoked from the repository root, where ``clean_install`` is
# not otherwise importable. Keep imports anchored to this checkout before the
# catalog validator or Alembic modules are loaded.
sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agro_labctl  # noqa: E402

INSTALL_REVISION = "deepfarms_clean_install_v1"
AUTHORIZED_ROOT = Path("/tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3f")
AUTHORIZED_DATABASE = "agro_hml_dbdcc24872aa_d3f"


def _preflight(root: Path) -> tuple[dict[str, str], dict[str, str], dict[str, object]]:
    if root.resolve() != AUTHORIZED_ROOT:
        raise agro_labctl.GateError(
            "Clean install deste runner está vinculado exclusivamente ao root D3F autorizado."
        )
    api_envs, _, _ = agro_labctl.validate_all(root)
    inherited = [
        key
        for key, value in os.environ.items()
        if value
        and (
            key.startswith(("AWS_", "S3_"))
            or key in agro_labctl.PROVIDER_KEYS
            or (
                any(
                    token in key
                    for token in ("API_KEY", "CLIENT_SECRET", "WEBHOOK_SECRET")
                )
                and key not in agro_labctl.INTERNAL_SECRETS
            )
        )
    ]
    if inherited:
        raise agro_labctl.GateError(
            "Ambiente do processo contém variáveis de provedores/cloud; limpe o ambiente e tente novamente."
        )
    api_env = api_envs[0]
    migration_env, migration_db = agro_labctl.validate_migration_env(root, api_env)
    if urlparse(api_env["DATABASE_URL"]).path.lstrip("/") != AUTHORIZED_DATABASE:
        raise agro_labctl.GateError(
            "Database não corresponde ao alvo D3F fixado no runner."
        )
    approval = agro_labctl.validate_migration_approval(root, api_env, INSTALL_REVISION)
    if approval.get("database") != AUTHORIZED_DATABASE:
        raise agro_labctl.GateError("Aprovação não está vinculada ao database D3F.")
    from clean_install.manifest import verify_artifact_hashes

    try:
        verify_artifact_hashes(API_ROOT)
    except (OSError, RuntimeError) as exc:
        raise agro_labctl.GateError(
            "Hashes fixados dos artefatos de clean install não conferem."
        ) from exc
    return api_env, migration_env, {"approval": approval, "migration_db": migration_db}


def _validate_database_identity(identity: tuple[object, ...], expected_user: str) -> None:
    """Fail closed on any database, role, endpoint or port mismatch."""
    if len(identity) != 4:
        raise agro_labctl.GateError("Resposta de identidade PostgreSQL inválida.")
    database, session_user, address, port = identity
    # PostgreSQL inet text may include its full host mask; accept only the
    # exact authorized loopback forms and never a prefix match.
    if (
        database != AUTHORIZED_DATABASE
        or session_user != expected_user
        or address not in {"127.0.0.1", "127.0.0.1/32"}
        or port != 5433
    ):
        raise agro_labctl.GateError(
            "Identidade PostgreSQL efetiva diverge do D3F loopback autorizado."
        )


def _validate_empty_database(
    *, schema_exists: bool, application_objects: int, version_objects: tuple[object, ...]
) -> None:
    """Reject pre-existing target schema or application/version relations."""
    if schema_exists:
        raise agro_labctl.GateError(
            "Schema farms já existe; instalação limpa recusada sem modificar o database."
        )
    if application_objects or any(version_objects):
        raise agro_labctl.GateError(
            "D3F não está vazio; instalação recusada sem modificar seus objetos."
        )


async def _execute_install(migration_env: dict[str, str], config) -> dict[str, int]:
    from sqlalchemy import text
    from clean_install.catalog_validation import validate_catalog
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        migration_env["DATABASE_URL"], connect_args={"timeout": 5}
    )
    try:
        async with engine.begin() as connection:

            def install_atomically(sync_connection):
                identity = sync_connection.execute(
                    text(
                        "SELECT current_database(), session_user, host(inet_server_addr()), inet_server_port()"
                    )
                ).one()
                parsed = urlparse(migration_env["DATABASE_URL"])
                _validate_database_identity(identity, parsed.username or "")
                schema_exists = sync_connection.execute(
                    text("SELECT to_regnamespace('farms') IS NOT NULL")
                ).scalar_one()
                app_objects = sync_connection.execute(
                    text("""
                    SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname NOT IN ('pg_catalog','information_schema')
                      AND n.nspname NOT LIKE 'pg_toast%'
                      AND c.relkind IN ('r','p','v','m','S','f')
                    """)
                ).scalar_one()
                versions = sync_connection.execute(
                    text(
                        "SELECT to_regclass('farms.deepfarms_install_version'), to_regclass('farms.alembic_version')"
                    )
                ).one()
                _validate_empty_database(
                    schema_exists=bool(schema_exists),
                    application_objects=app_objects,
                    version_objects=versions,
                )
                from clean_install.manifest import verify_artifact_hashes

                hashes = verify_artifact_hashes(API_ROOT)
                config.attributes["connection"] = sync_connection
                from alembic import command

                command.upgrade(config, INSTALL_REVISION)
                return validate_catalog(
                    sync_connection, expected_manifest=hashes, check_version=True
                )

            return await connection.run_sync(install_atomically)
    finally:
        await engine.dispose()


def run(root: Path) -> int:
    api_env, migration_env, _ = _preflight(root)
    # The only accepted live gates are the official lab gates. They are repeated
    # by env.py immediately before Alembic executes the revision.
    args = argparse.Namespace(root=root)
    if agro_labctl.cmd_identity(args) != 0:
        raise agro_labctl.GateError("Gate identity não aprovou o laboratório.")
    if agro_labctl.cmd_migration_identity(args) != 0:
        raise agro_labctl.GateError("Gate migration-identity não aprovou o alvo.")
    # Settings reads process variables before .env.local. Replace database and
    # staging values with the private synthetic migration file; do not source a
    # dotenv or pass credentials in argv/log output.
    os.environ["AGRO_LAB_ROOT"] = str(root)
    for key, value in migration_env.items():
        os.environ[key] = value
    os.environ["DATABASE_URL"] = migration_env["DATABASE_URL"]
    from alembic.config import Config

    config = Config(str(API_ROOT / "migrations" / "clean_install" / "alembic.ini"))
    config.set_main_option(
        "script_location", str(API_ROOT / "migrations" / "clean_install")
    )
    config.set_main_option(
        "sqlalchemy.url", migration_env["DATABASE_URL"].replace("%", "%%")
    )
    catalog = asyncio.run(_execute_install(migration_env, config))
    print(
        f"Clean install aplicada e validada: {INSTALL_REVISION}; database={AUTHORIZED_DATABASE}; catalog={catalog}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    try:
        sys.exit(run(parser.parse_args().root))
    except agro_labctl.GateError as exc:
        print(f"NO-GO: {exc}", file=sys.stderr)
        sys.exit(2)
