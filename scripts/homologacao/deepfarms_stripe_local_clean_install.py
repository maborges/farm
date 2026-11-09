#!/usr/bin/env python3
"""Install only deepfarms_clean_install_v1 into Lauro's disposable Stripe DB."""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sqlalchemy.engine import URL, make_url

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

INSTALL_REVISION = "deepfarms_clean_install_v1"
EXPECTED_HOST = "127.0.0.1"
EXPECTED_PORT = 55432
EXPECTED_POSTGRES_PORT = 5432
EXPECTED_DATABASE = "deepfarms_stripe_test"
EXPECTED_USER = "stripe_test"


class InstallGateError(RuntimeError):
    """Raised when the explicitly authorized disposable target is not proven."""


def _target_url(password: str | None = None) -> str:
    return URL.create(
        "postgresql+asyncpg",
        username=EXPECTED_USER,
        password=password,
        host=EXPECTED_HOST,
        port=EXPECTED_PORT,
        database=EXPECTED_DATABASE,
    ).render_as_string(hide_password=False)


def _resolve_password(environ: Mapping[str, str] | None = None) -> str:
    """Read only explicit local password variables; never fall back to dotenv."""
    source = os.environ if environ is None else environ
    password = source.get("DEEPFARMS_STRIPE_TEST_PASSWORD") or source.get("PGPASSWORD")
    if not password:
        raise InstallGateError(
            "Credencial ausente: defina DEEPFARMS_STRIPE_TEST_PASSWORD ou PGPASSWORD no processo local."
        )
    return password


def _validate_target_url(database_url: str) -> None:
    try:
        target = make_url(database_url)
    except (TypeError, ValueError) as exc:
        raise InstallGateError("URL do alvo PostgreSQL inválida.") from exc
    if (
        target.drivername != "postgresql+asyncpg"
        or target.host != EXPECTED_HOST
        or target.port != EXPECTED_PORT
        or target.database != EXPECTED_DATABASE
        or target.username != EXPECTED_USER
        or target.query
    ):
        raise InstallGateError(
            "Destino recusado: somente 127.0.0.1:55432/deepfarms_stripe_test como stripe_test é permitido."
        )


def _validate_database_identity(
    identity: tuple[Any, ...], authorized_container_addresses: frozenset[str]
) -> None:
    if len(identity) != 5:
        raise InstallGateError("Resposta de identidade PostgreSQL inválida.")
    database, session_user, address, port, version_num = identity
    try:
        internal_address = str(ipaddress.ip_address(str(address)))
    except ValueError as exc:
        raise InstallGateError("Endereço interno PostgreSQL inválido.") from exc
    if (
        database != EXPECTED_DATABASE
        or session_user != EXPECTED_USER
        or internal_address not in authorized_container_addresses
        or port != EXPECTED_POSTGRES_PORT
        or int(version_num) // 10000 != 16
    ):
        raise InstallGateError(
            "Identidade PostgreSQL efetiva diverge do PostgreSQL 16 descartável autorizado."
        )


def _container_internal_addresses(
    *, running: bool, port_bindings: Mapping[str, Any], networks: Mapping[str, Any]
) -> frozenset[str]:
    """Validate the disposable container's published port and return its IPs."""
    if not running:
        raise InstallGateError("Container PostgreSQL autorizado não está ativo.")
    bindings = port_bindings.get("5432/tcp")
    if bindings != [{"HostIp": EXPECTED_HOST, "HostPort": str(EXPECTED_PORT)}]:
        raise InstallGateError(
            "Container recusado: publicação deve ser exclusivamente 127.0.0.1:55432 → 5432/tcp."
        )

    addresses: set[str] = set()
    for network in networks.values():
        raw_address = network.get("IPAddress") if isinstance(network, Mapping) else None
        if not raw_address:
            continue
        try:
            parsed = ipaddress.ip_address(raw_address)
        except ValueError as exc:
            raise InstallGateError("Container possui endereço de rede inválido.") from exc
        if (
            not isinstance(parsed, ipaddress.IPv4Address)
            or not parsed.is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_multicast
            or parsed.is_unspecified
            or parsed.is_reserved
        ):
            raise InstallGateError(
                "Container possui endereço que não pertence a uma rede IPv4 privada autorizável."
            )
        addresses.add(str(parsed))
    if not addresses:
        raise InstallGateError("Não foi possível obter IP privado do container autorizado.")
    return frozenset(addresses)


def _resolve_authorized_container_addresses() -> frozenset[str]:
    """Resolve only Docker metadata for the unique container publishing our target port."""
    try:
        listed = subprocess.run(
            ["docker", "ps", "--filter", f"publish={EXPECTED_PORT}", "--format", "{{.ID}}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        container_ids = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
        if len(container_ids) != 1:
            raise InstallGateError(
                "É necessário exatamente um container ativo publicando a porta autorizada."
            )
        inspected = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Running}}|{{json .NetworkSettings.Ports}}|{{json .NetworkSettings.Networks}}",
                container_ids[0],
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstallGateError(
            "Não foi possível verificar os metadados do container PostgreSQL autorizado."
        ) from exc

    try:
        running_text, bindings_json, networks_json = inspected.stdout.strip().split("|", 2)
        port_bindings = json.loads(bindings_json)
        networks = json.loads(networks_json)
    except (ValueError, json.JSONDecodeError) as exc:
        raise InstallGateError("Metadados Docker do container autorizado são inválidos.") from exc
    if not isinstance(port_bindings, Mapping) or not isinstance(networks, Mapping):
        raise InstallGateError("Metadados Docker do container autorizado são inválidos.")
    return _container_internal_addresses(
        running=running_text.strip().lower() == "true",
        port_bindings=port_bindings,
        networks=networks,
    )


def _validate_empty_database(
    *, schema_exists: bool, application_objects: int, migration_history: bool
) -> None:
    if schema_exists or application_objects or migration_history:
        raise InstallGateError(
            "Instalação recusada: o banco já contém schema farms, objetos de aplicação ou histórico de migrações."
        )


async def _install(database_url: str) -> dict[str, int]:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import MetaData, Table, func, select, text
    from sqlalchemy.ext.asyncio import create_async_engine

    from clean_install import INSTALL_VERSION
    from clean_install.catalog_validation import validate_catalog
    from clean_install.manifest import verify_artifact_hashes
    from clean_install.seed_contract import SEEDS

    if INSTALL_VERSION != INSTALL_REVISION:
        raise InstallGateError("A constante canônica da instalação mudou inesperadamente.")
    hashes = verify_artifact_hashes(API_ROOT)
    authorized_container_addresses = _resolve_authorized_container_addresses()
    engine = create_async_engine(database_url, connect_args={"timeout": 5})
    config = Config(str(API_ROOT / "migrations" / "clean_install" / "alembic.ini"))
    config.set_main_option(
        "script_location", str(API_ROOT / "migrations" / "clean_install")
    )
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

    try:
        async with engine.begin() as connection:
            def install_atomically(sync_connection):
                identity = sync_connection.execute(
                    text("""
                        SELECT current_database(), session_user,
                               host(inet_server_addr()), inet_server_port(),
                               current_setting('server_version_num')::integer
                    """)
                ).one()
                _validate_database_identity(identity, authorized_container_addresses)

                # Serialize install attempts before the read-only preflight.
                sync_connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                    {"key": INSTALL_REVISION},
                )
                schema_exists = sync_connection.execute(
                    text("SELECT to_regnamespace('farms') IS NOT NULL")
                ).scalar_one()
                application_objects = sync_connection.execute(
                    text("""
                        SELECT
                          (SELECT count(*)
                             FROM pg_class c
                             JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                              AND n.nspname NOT LIKE 'pg_toast%'
                              AND n.nspname NOT LIKE 'pg_temp_%'
                              AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f'))
                          + (SELECT count(*)
                               FROM pg_namespace
                              WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'public')
                                AND nspname NOT LIKE 'pg_%')
                          + (SELECT count(*)
                               FROM pg_proc p
                               JOIN pg_namespace n ON n.oid = p.pronamespace
                              WHERE n.nspname = 'public')
                          + (SELECT count(*)
                               FROM pg_type t
                               JOIN pg_namespace n ON n.oid = t.typnamespace
                              WHERE n.nspname = 'public'
                                AND t.typtype IN ('c', 'd', 'e', 'r')
                                AND t.typname NOT LIKE 'pg_%')
                    """)
                ).scalar_one()
                migration_history = sync_connection.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE c.relname IN (
                                'alembic_version', 'deepfarms_install_version'
                            )
                              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                        )
                    """)
                ).scalar_one()
                _validate_empty_database(
                    schema_exists=bool(schema_exists),
                    application_objects=int(application_objects),
                    migration_history=bool(migration_history),
                )

                # env.py receives both this exact URL and the already-verified
                # transaction; it cannot open a second connection elsewhere.
                config.attributes["connection"] = sync_connection
                command.upgrade(config, INSTALL_REVISION)
                catalog = validate_catalog(
                    sync_connection, expected_manifest=hashes, check_version=True
                )

                expected_counts = Counter(row.table for row in SEEDS)
                metadata = MetaData()
                observed_counts: dict[str, int] = {}
                for table_name, expected_count in sorted(expected_counts.items()):
                    table = Table(
                        table_name,
                        metadata,
                        schema="farms",
                        autoload_with=sync_connection,
                    )
                    observed = sync_connection.execute(
                        select(func.count()).select_from(table)
                    ).scalar_one()
                    if observed != expected_count:
                        raise InstallGateError(
                            f"Quantidade de registros do catálogo {table_name} diverge do manifesto."
                        )
                    observed_counts[table_name] = int(observed)

                recorded_version = sync_connection.execute(
                    text("SELECT version_num FROM farms.deepfarms_install_version")
                ).scalar_one()
                if recorded_version != INSTALL_REVISION:
                    raise InstallGateError(
                        f"Versão instalada diverge: esperado={INSTALL_REVISION}."
                    )
                if sync_connection.execute(
                    text("SELECT to_regclass('farms.alembic_version')")
                ).scalar_one_or_none() is not None:
                    raise InstallGateError(
                        "Histórico Alembic legado apareceu no destino da instalação limpa."
                    )
                return catalog | {"seed_catalog_rows": sum(observed_counts.values())}

            return await connection.run_sync(install_atomically)
    finally:
        await engine.dispose()


def run() -> int:
    # No DATABASE_URL, PGHOST, PGPORT, PGDATABASE, PGUSER, dotenv, or application
    # config is used to select the target. Only this purpose-specific password
    # may be supplied; all endpoint identity fields remain hard-coded above.
    password = _resolve_password()
    database_url = _target_url(password)
    _validate_target_url(database_url)
    os.environ["DATABASE_URL"] = database_url
    os.environ["REQUIRE_RESTRICTED_RUNTIME_ROLE"] = "false"
    os.environ["RLS_DEV_ROUTE_SESSIONS_ENABLED"] = "false"
    os.environ["RLS_DEV_ALL_ROUTES_ENABLED"] = "false"
    os.environ["AUTHENTICATION_DATABASE_URL"] = ""
    os.environ["RECOMMENDATION_DISPATCHER_DATABASE_URL"] = ""

    catalog = asyncio.run(_install(database_url))
    print(
        f"Instalação validada: {INSTALL_REVISION}; "
        f"database={EXPECTED_DATABASE}; catalog={catalog}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        sys.exit(run())
    except InstallGateError as exc:
        print(f"NO-GO: {exc}", file=sys.stderr)
        sys.exit(2)
