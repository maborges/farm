#!/usr/bin/env python3
"""Provision a database-scoped migration role in a new, empty lab database.

This command never edits an existing product database. It is intentionally
separate from `agro_labctl migrate`; role provisioning does not authorize DDL.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import secrets
import stat
import sys
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agro_labctl as labctl  # noqa: E402


class ProvisionError(RuntimeError):
    pass


def _ident(value: str) -> str:
    if not value.replace("_", "").isalnum() or not value or not (value[0].isalpha() or value[0] == "_"):
        raise ProvisionError("Identificador PostgreSQL inválido.")
    return '"' + value.replace('"', '""') + '"'


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_role_ddl(role: str, password: str, database: str) -> str:
    role_sql, db_sql = _ident(role), _ident(database)
    password_sql = _literal(password)
    return "\n".join(
        (
            "BEGIN;",
            f"CREATE ROLE {role_sql} LOGIN PASSWORD {password_sql} NOINHERIT "
            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS "
            "CONNECTION LIMIT 5;",
            f"REVOKE ALL ON DATABASE {db_sql} FROM PUBLIC;",
            f"GRANT CONNECT, CREATE ON DATABASE {db_sql} TO {role_sql};",
            "COMMIT;",
        )
    )


def _write_private_exclusive(path: Path, content: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _migration_url(api_url: str, role: str, password: str) -> str:
    parsed = urlparse(api_url)
    host = parsed.hostname or "127.0.0.1"
    netloc = f"{quote(role, safe='')}:{quote(password, safe='')}@{host}:{parsed.port}"
    return urlunparse(("postgresql+asyncpg", netloc, parsed.path, "", "", ""))


async def _provision(root: Path, admin_env_path: Path, requested_db: str, confirmation: str) -> None:
    root = root.resolve()
    apis, _, _ = labctl.validate_all(root)
    api_url = apis[0]["DATABASE_URL"]
    target = urlparse(api_url)
    database = (target.path or "").lstrip("/")
    instance = apis[0]["STAGING_INSTANCE_ID"]
    role = labctl.expected_migration_role(instance, database)
    admin_env_path = admin_env_path.resolve()

    if requested_db != database or confirmation != database:
        raise ProvisionError("Database solicitado e confirmação devem corresponder exatamente ao env do laboratório.")
    if not admin_env_path.is_relative_to(root / "config"):
        raise ProvisionError("Arquivo administrativo deve ficar no diretório config privado do laboratório.")
    try:
        if stat.S_IMODE(admin_env_path.stat().st_mode) != 0o600:
            raise ProvisionError("Arquivo administrativo precisa ter modo 0600.")
    except OSError:
        raise ProvisionError("Arquivo administrativo privado ausente ou inacessível.") from None
    admin_env = labctl.read_env(admin_env_path)
    if set(admin_env) != {"DATABASE_URL"}:
        raise ProvisionError("Arquivo administrativo deve conter somente DATABASE_URL sintética.")
    admin = urlparse(admin_env["DATABASE_URL"])
    expected_admin = "agro_hml_owner_" + "".join(c for c in instance.lower() if c.isalnum())[:12]
    if (
        admin.scheme not in {"postgresql", "postgresql+asyncpg"}
        or admin.hostname != "127.0.0.1"
        or admin.port != 5433
        or (admin.path or "").lstrip("/") != database
        or admin.username != expected_admin
        or not admin.password
        or admin.query
        or admin.fragment
    ):
        raise ProvisionError("Conexão administrativa não corresponde ao owner sintético do alvo loopback.")

    manifest_path = root / "config" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("instance_id") != instance
        or manifest.get("database") != database
        or manifest.get("migration_role") != role
    ):
        raise ProvisionError("ID da instância diverge do manifesto privado.")
    final_path = root / "config" / "alembic-migration.env"
    if final_path.exists():
        raise ProvisionError("Configuração Alembic já existe; provisionamento não sobrescreve identidades.")

    postgres = manifest.get("services", {}).get("postgres", {})
    cluster_root_name = f"deepfarms-agro-hml-{instance}"
    config_root_suffix = root.name[len(cluster_root_name) + 1 :] if root.name.startswith(cluster_root_name + "-") else ""
    try:
        expected_pgdata = Path(postgres["data_directory"]).resolve()
        expected_pid = int(postgres["pid"])
        recorded_version = str(postgres["version"])
        pid_from_file = int((expected_pgdata / "postmaster.pid").read_text().splitlines()[0])
        process_cmdline = Path(f"/proc/{expected_pid}/cmdline").read_bytes().replace(b"\0", b" ")
    except (KeyError, OSError, ValueError, IndexError):
        raise ProvisionError("Manifesto/PGDATA/PID do cluster isolado não podem ser comprovados.") from None
    if (
        root.parent != Path("/tmp")
        or (
            root.name != cluster_root_name
            and not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", config_root_suffix)
        )
        or expected_pgdata != Path("/tmp") / f"deepfarms-agro-hml-{instance}" / "postgres" / "data"
        or expected_pid < 2
        or pid_from_file != expected_pid
        or str(expected_pgdata).encode() not in process_cmdline
        or postgres.get("state") != "running"
        or postgres.get("database") != database
        or postgres.get("host") != "127.0.0.1"
        or postgres.get("port") != 5433
        or not recorded_version.startswith("16.")
    ):
        raise ProvisionError("Cluster/PGDATA/PID divergem do manifesto do laboratório; nenhum DDL executado.")

    password = secrets.token_urlsafe(36)
    migration_url = _migration_url(api_url, role, password)
    migration_env = dict(apis[0], DATABASE_URL=migration_url)
    pending_path = root / "config" / f".alembic-migration-{secrets.token_hex(8)}.pending"
    content = "".join(f"{key}={value}\n" for key, value in migration_env.items())
    _write_private_exclusive(pending_path, content)

    import asyncpg

    admin_url = admin_env["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    ddl_attempted = False
    try:
        conn = await asyncpg.connect(admin_url, timeout=5)
        try:
            identity = await conn.fetchrow(
                """SELECT current_database() AS database, current_user AS username,
                          inet_server_addr()::text AS address, inet_server_port() AS port,
                          current_setting('server_version') AS version,
                          current_setting('data_directory') AS data_directory,
                          pg_get_userbyid(d.datdba) AS owner,
                          (SELECT count(*) FROM pg_namespace n
                           WHERE n.nspname NOT IN ('pg_catalog','information_schema','public')
                             AND n.nspname NOT LIKE 'pg_toast%') AS user_schemas,
                          (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                           WHERE n.nspname NOT IN ('pg_catalog','information_schema')
                             AND n.nspname NOT LIKE 'pg_toast%'
                             AND c.relkind IN ('r','p','v','m','S','f')) AS user_relations,
                          EXISTS (SELECT 1 FROM pg_roles WHERE rolname=$1) AS role_exists,
                          (SELECT rolsuper AND rolcreatedb AND rolcreaterole AND rolreplication
                                  AND rolbypassrls FROM pg_roles WHERE rolname=$2) AS admin_attributes,
                          EXISTS (SELECT 1 FROM pg_roles WHERE rolname=$3 AND rolcanlogin) AS app_role_exists,
                          has_database_privilege($3, current_database(), 'CONNECT') AS app_connect
                     FROM pg_database d WHERE d.datname=current_database()""",
                role,
                expected_admin,
                target.username,
            )
            if (
                identity is None
                or identity["database"] != database
                or identity["username"] != expected_admin
                or identity["address"] not in {"127.0.0.1", "127.0.0.1/32"}
                or identity["port"] != 5433
                or not identity["version"].startswith(recorded_version)
                or Path(identity["data_directory"]).resolve() != expected_pgdata
                or identity["owner"] != expected_admin
                or identity["user_schemas"] != 0
                or identity["user_relations"] != 0
                or identity["role_exists"]
                or identity["admin_attributes"] is not True
                or identity["app_role_exists"] is not True
                or identity["app_connect"] is not True
            ):
                raise ProvisionError("Preflight recusou alvo não vazio, role existente ou identidade divergente.")
            ddl_attempted = True
            await conn.execute(build_role_ddl(role, password, database))
        finally:
            await conn.close()

        # Hard-link is atomic and refuses to overwrite a concurrently created file.
        os.link(pending_path, final_path)
        pending_path.unlink()
        os.chmod(final_path, 0o600)
    except ProvisionError:
        if not ddl_attempted:
            pending_path.unlink(missing_ok=True)
        raise
    except Exception:
        if not ddl_attempted:
            pending_path.unlink(missing_ok=True)
        # Once DDL is attempted, retain the mode-0600 credential staging file
        # because commit outcome can be ambiguous after a lost connection.
        raise ProvisionError(
            "Provisionamento falhou; não repita automaticamente. Se DDL foi tentado, "
            f"credencial pendente preservada em {pending_path}."
        ) from None

    try:
        labctl.cmd_migration_identity(argparse.Namespace(root=root))
    except labctl.GateError:
        raise
    print(f"Role migradora exclusiva para {database}; gate oficial PASS; credencial privada em {final_path}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--admin-env", type=Path, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--apply", action="store_true", help="Confirma provisionamento do alvo vazio especificado.")
    args = parser.parse_args()
    if not args.apply:
        parser.error("--apply é obrigatório; o script nunca provisiona em modo implícito.")
    try:
        asyncio.run(_provision(args.root, args.admin_env, args.database, args.confirm_database))
    except (ProvisionError, labctl.GateError) as exc:
        print(f"NO-GO: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
