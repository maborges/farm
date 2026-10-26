#!/usr/bin/env python3
"""Controlador fail-closed do laboratório local AGRO-ADMIN-01H2C.

Não provisiona nem inicia PostgreSQL/Redis. Comandos de aplicação exigem envs
gerados pelo subcomando prepare e um gate aprovado. Segredos nunca são impressos.
"""
# Every subprocess below uses an argv list, a fixed executable allowlist, and
# validated loopback-only arguments; shell execution is never enabled.
# ruff: noqa: S603

from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shlex
import signal
import socket
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = Path(tempfile.gettempdir())
PROVIDER_KEYS = (
    "OPENWEATHER_API_KEY",
    "WEATHERAPI_API_KEY",
    "TOMORROWIO_API_KEY",
    "STRIPE_SECRET_KEY",
    "ASAAS_API_KEY",
    "SANKHYA_CLIENT_SECRET",
    "SANKHYA_X_TOKEN",
    "TARA_CLIENT_SECRET",
    "BALANCA_WEBHOOK_SECRET",
)
INTERNAL_SECRETS = {"JWT_SECRET_KEY", "PLATFORM_CREDENTIALS_MASTER_KEY", "INTEGRATIONS_SECRET_KEY"}
API_REQUIRED = (
    "ENVIRONMENT",
    "APP_ENV",
    "DATABASE_URL",
    "REDIS_URL",
    "STORAGE_BACKEND",
    "STORAGE_LOCAL_PATH",
    "JWT_SECRET_KEY",
    "PLATFORM_CREDENTIALS_MASTER_KEY",
    "INTEGRATIONS_SECRET_KEY",
    "STAGING_INSTANCE_ID",
)


class GateError(RuntimeError):
    pass


def say(message: str) -> None:
    print(message, flush=True)


def read_env(path: Path) -> dict[str, str]:
    """Read a strict KEY=value file; do not source arbitrary shell code."""
    values: dict[str, str] = {}
    if not path.is_file():
        raise GateError(f"Arquivo de configuração ausente: {path}")
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*=.*", line):
            raise GateError(f"Formato inválido em {path.name}, linha {number}.")
        key, value = line.split("=", 1)
        value = value.strip()
        if value.startswith(('"', "'")):
            try:
                value = shlex.split(value)[0]
            except (ValueError, IndexError):
                raise GateError(f"Valor inválido em {path.name}, linha {number}.") from None
        values[key] = value
    return values


def local_env_keys() -> set[str]:
    """Read variable names only; never expose or use values from the commercial dotenv."""
    path = ROOT / "services/api/.env.local"
    if not path.is_file():
        return set()
    keys: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    return keys


def secret_looks_synthetic(value: str) -> bool:
    return len(value) >= 32 and value not in {"change-me", "changeme", "secret", "password"}


def validate_api_env(path: Path, instance_root: Path) -> dict[str, str]:
    values = read_env(path)
    missing_dotenv_overrides = sorted(local_env_keys() - values.keys())
    if missing_dotenv_overrides:
        raise GateError(
            "Env do laboratório não sobrescreve todas as chaves presentes no dotenv local: "
            + ", ".join(missing_dotenv_overrides)
        )
    absent = [key for key in API_REQUIRED if not values.get(key)]
    if absent:
        raise GateError(f"Variáveis obrigatórias ausentes em {path.name}: {', '.join(absent)}")
    if values["ENVIRONMENT"] != "staging" or values["APP_ENV"] != "staging":
        raise GateError("ENVIRONMENT e APP_ENV precisam ser staging.")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{6,40}", values["STAGING_INSTANCE_ID"]):
        raise GateError("STAGING_INSTANCE_ID inválido.")
    if values.get("FRONTEND_URL") not in {"http://127.0.0.1:3001", "http://127.0.0.1:3005"}:
        raise GateError("FRONTEND_URL deve usar uma origem loopback do laboratório.")
    try:
        origins = json.loads(values.get("ALLOW_ORIGINS", "[]"))
    except json.JSONDecodeError:
        raise GateError("ALLOW_ORIGINS precisa ser uma lista JSON explícita.") from None
    if (
        not isinstance(origins, list)
        or not origins
        or any(
            origin not in {"http://127.0.0.1:3001", "http://127.0.0.1:3005"} for origin in origins
        )
    ):
        raise GateError("ALLOW_ORIGINS contém origem fora da allowlist local.")

    db = urlparse(values["DATABASE_URL"])
    if db.scheme not in {"postgresql+asyncpg", "postgresql"}:
        raise GateError("DATABASE_URL deve usar PostgreSQL; fallback SQLite é proibido.")
    if db.hostname not in {"127.0.0.1", "localhost", "::1"} or db.port != 5433:
        raise GateError("DATABASE_URL deve apontar para loopback:5433.")
    raw_db_name = (db.path or "").lstrip("/")
    db_name = raw_db_name.lower()
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,62}", raw_db_name):
        raise GateError("Nome de database inválido para conexão restrita.")
    if not (
        db_name.startswith(("agro_hml_", "deepfarms_hml_", "agro_staging_", "deepfarms_staging_"))
        or db_name.endswith("_test")
    ) or any(x in db_name for x in ("prod", "commercial", "shared")):
        raise GateError(
            "Nome do database não identifica claramente um alvo descartável de homologação."
        )
    if not db.username or not db.password:
        raise GateError("DATABASE_URL precisa de usuário e senha próprios de homologação.")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,62}", db.username):
        raise GateError("Usuário PostgreSQL inválido para conexão restrita.")

    redis = urlparse(values["REDIS_URL"])
    if (
        redis.scheme != "redis"
        or redis.hostname not in {"127.0.0.1", "localhost", "::1"}
        or redis.port != 6380
    ):
        raise GateError("REDIS_URL deve apontar para redis loopback:6380.")
    if not redis.password or redis.path not in {
        "/0",
        "/1",
        "/2",
        "/3",
        "/4",
        "/5",
        "/6",
        "/7",
        "/8",
        "/9",
        "/10",
        "/11",
        "/12",
        "/13",
        "/14",
        "/15",
    }:
        raise GateError("REDIS_URL exige autenticação e database Redis explícito.")

    if values["STORAGE_BACKEND"].lower() != "local":
        raise GateError("Somente STORAGE_BACKEND=local é aceito.")
    storage = Path(values["STORAGE_LOCAL_PATH"]).resolve()
    expected = instance_root.resolve() / "uploads"
    if storage != expected or storage == DEFAULT_ROOT / "agrosaas_uploads":
        raise GateError(
            "STORAGE_LOCAL_PATH precisa ser exatamente o diretório uploads exclusivo da instância."
        )
    for key in ("S3_BUCKET", "S3_BUCKET_NAME", "S3_ENDPOINT_URL", "S3_ACCESS_KEY", "S3_SECRET_KEY"):
        if values.get(key):
            raise GateError(
                "Configuração S3/MinIO detectada; o laboratório aceita apenas storage local."
            )
    provider_configured = [
        key
        for key, value in values.items()
        if value
        and re.search(
            r"(API_KEY|ACCESS_KEY|CLIENT_SECRET|WEBHOOK_SECRET|_TOKEN$|TOKEN$|SECRET_KEY)", key
        )
        and key not in INTERNAL_SECRETS
    ]
    if provider_configured or any(values.get(key) for key in PROVIDER_KEYS):
        raise GateError(
            "Credencial de provedor externo presente; use somente mocks/fixtures sem secrets."
        )
    for key in ("JWT_SECRET_KEY", "PLATFORM_CREDENTIALS_MASTER_KEY", "INTEGRATIONS_SECRET_KEY"):
        if not secret_looks_synthetic(values[key]):
            raise GateError(f"{key} ausente ou fraca; use valor sintético exclusivo de teste.")
    manifest_path = instance_root / "config" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise GateError("Manifesto sintético de configuração ausente ou inválido.") from None
    if manifest.get("instance_id") != values["STAGING_INSTANCE_ID"]:
        raise GateError("ID da instância diverge do manifesto sintético.")
    for key in ("JWT_SECRET_KEY", "PLATFORM_CREDENTIALS_MASTER_KEY", "INTEGRATIONS_SECRET_KEY"):
        if hashlib.sha256(values[key].encode()).hexdigest() != manifest.get(
            "secret_sha256", {}
        ).get(key):
            raise GateError(
                "Segredos de aplicação não correspondem à configuração sintética gerada."
            )

    # Pydantic Settings dá precedência ao processo sobre env_file. Exigir overrides
    # explícitos aqui impede uso silencioso dos valores de services/api/.env.local.
    for key in API_REQUIRED:
        if not values.get(key):
            raise GateError(f"Override explícito obrigatório para {key}.")
    return values


def validate_front_env(path: Path, kind: str) -> dict[str, str]:
    values = read_env(path)
    if kind == "web":
        url = values.get("BACKEND_URL", "")
        if url != "http://127.0.0.1:8001":
            raise GateError("BACKEND_URL do Backoffice deve ser http://127.0.0.1:8001.")
        port = 3001
    else:
        url = values.get("AGRO_API_INTERNAL_ORIGIN", "")
        if url != "http://127.0.0.1:8001":
            raise GateError("AGRO_API_INTERNAL_ORIGIN deve ser http://127.0.0.1:8001.")
        port = 3005
    for key in ("NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_WS_URL"):
        if values.get(key):
            allowed = {
                "NEXT_PUBLIC_API_URL": {"http://127.0.0.1:8001", "http://127.0.0.1:8002"},
                "NEXT_PUBLIC_WS_URL": {"ws://127.0.0.1:8001", "ws://127.0.0.1:8002"},
            }[key]
            if values[key].rstrip("/") not in allowed:
                raise GateError(f"{key} precisa apontar para loopback.")
    values["_LAB_PORT"] = str(port)
    return values


def validate_all(root: Path) -> tuple[list[dict[str, str]], dict[str, str], dict[str, str]]:
    inherited = [
        key
        for key, value in os.environ.items()
        if value
        and re.search(
            r"(API_KEY|ACCESS_KEY|CLIENT_SECRET|WEBHOOK_SECRET|_TOKEN$|TOKEN$|SECRET_KEY|SMTP_PASS|MAIL_PASS)",
            key,
        )
        and key not in INTERNAL_SECRETS
    ]
    if inherited:
        raise GateError(
            "O ambiente do processo contém possíveis credenciais externas; "
            "limpe-o antes do laboratório."
        )
    for key in ("BACKEND_URL", "AGRO_API_INTERNAL_ORIGIN"):
        inherited_url = os.environ.get(key, "")
        if inherited_url and inherited_url != "http://127.0.0.1:8001":
            raise GateError("O ambiente do processo contém URL de backend fora da allowlist local.")
    for key in ("NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_WS_URL"):
        inherited_url = os.environ.get(key, "")
        allowed = {
            "NEXT_PUBLIC_API_URL": {"http://127.0.0.1:8001", "http://127.0.0.1:8002"},
            "NEXT_PUBLIC_WS_URL": {"ws://127.0.0.1:8001", "ws://127.0.0.1:8002"},
        }[key]
        if inherited_url and inherited_url.rstrip("/") not in allowed:
            raise GateError("O ambiente do processo contém URL pública fora da allowlist local.")
    env_dir = root / "config"
    apis = [validate_api_env(env_dir / f"api{i}.env", root) for i in (1, 2)]
    if apis[0]["STAGING_INSTANCE_ID"] != apis[1]["STAGING_INSTANCE_ID"]:
        raise GateError("Os dois processos devem pertencer à mesma instância isolada.")
    for key in ("DATABASE_URL", "REDIS_URL", "STORAGE_LOCAL_PATH"):
        if apis[0][key] != apis[1][key]:
            raise GateError(f"API 1 e API 2 precisam compartilhar {key} do laboratório.")
    web = validate_front_env(env_dir / "web.env", "web")
    agro = validate_front_env(env_dir / "agro.env", "agro")
    return apis, web, agro


def cmd_prepare(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if (
        root.parent != DEFAULT_ROOT and not root.is_relative_to(DEFAULT_ROOT)
    ) or not root.name.startswith("deepfarms-agro-hml-"):
        raise GateError("Por segurança, a instância deve ficar sob /tmp.")
    if root.exists():
        raise GateError("Diretório já existe; prepare não sobrescreve dados existentes.")
    instance = root.name.replace("deepfarms-agro-hml-", "")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{6,40}", instance):
        raise GateError("Use diretório /tmp/deepfarms-agro-hml-<id> com id de 6 a 40 caracteres.")
    user = "agro_hml_" + re.sub(r"[^a-z0-9]", "", instance.lower())[:12]
    dbname = "agro_hml_" + re.sub(r"[^a-z0-9]", "", instance.lower())[:12]
    dbpass = secrets.token_urlsafe(28)
    redispass = secrets.token_urlsafe(28)
    jwt = secrets.token_urlsafe(40)
    master = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    integrations = secrets.token_urlsafe(40)
    root.mkdir(mode=0o700, parents=False)
    (root / "config").mkdir(mode=0o700)
    (root / "uploads").mkdir(mode=0o700)
    (root / "run").mkdir(mode=0o700)
    (root / "logs").mkdir(mode=0o700)
    encoded_user = quote(user, safe="")
    encoded_pass = quote(dbpass, safe="")
    base = {key: "" for key in local_env_keys()}
    base.update(
        {
            "ENVIRONMENT": "staging",
            "APP_ENV": "staging",
            "DATABASE_URL": f"postgresql+asyncpg://{encoded_user}:{encoded_pass}@127.0.0.1:5433/{dbname}",
            "REDIS_URL": f"redis://:{quote(redispass, safe='')}@127.0.0.1:6380/0",
            "STORAGE_BACKEND": "local",
            "STORAGE_LOCAL_PATH": str(root / "uploads"),
            "JWT_SECRET_KEY": jwt,
            "PLATFORM_CREDENTIALS_MASTER_KEY": master,
            "INTEGRATIONS_SECRET_KEY": integrations,
            "STAGING_INSTANCE_ID": instance,
            "OPENWEATHER_API_KEY": "",
            "WEATHERAPI_API_KEY": "",
            "TOMORROWIO_API_KEY": "",
            "STRIPE_SECRET_KEY": "",
            "ASAAS_API_KEY": "",
            "SANKHYA_CLIENT_SECRET": "",
            "SANKHYA_X_TOKEN": "",
            "TARA_CLIENT_SECRET": "",
            "BALANCA_WEBHOOK_SECRET": "",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "10080",
            "ALLOW_ORIGINS": '["http://127.0.0.1:3001","http://127.0.0.1:3005"]',
            "ANTHROPIC_API_KEY": "",
            "FRONTEND_URL": "http://127.0.0.1:3005",
            "IA_MODEL": "mock",
            "JWT_ALGORITHM": "HS256",
            "MAIL_FROM": "hml@example.invalid",
            "S3_ACCESS_KEY": "",
            "S3_BUCKET": "",
            "S3_ENDPOINT_URL": "",
            "S3_REGION": "us-east-1",
            "S3_SECRET_KEY": "",
            "SMTP_HOST": "",
            "SMTP_PASS": "",
            "SMTP_PORT": "2525",
            "SMTP_USER": "",
            "STRIPE_WEBHOOK_SECRET": "",
            "WHATSAPP_COMERCIAL_NUMERO": "",
        }
    )
    for i in (1, 2):
        values = dict(base, WORKER_ID=f"agro-hml-{instance}-{i}")
        (root / "config" / f"api{i}.env").write_text(
            "".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8"
        )
        (root / "config" / f"api{i}.env").chmod(0o600)
    manifest = {
        "instance_id": instance,
        "database": dbname,
        "migration_role": expected_migration_role(instance, dbname),
        "secret_sha256": {
            key: hashlib.sha256(base[key].encode()).hexdigest()
            for key in (
                "JWT_SECRET_KEY",
                "PLATFORM_CREDENTIALS_MASTER_KEY",
                "INTEGRATIONS_SECRET_KEY",
            )
        },
    }
    manifest_path = root / "config" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    for name, values in (
        ("web.env", {"BACKEND_URL": "http://127.0.0.1:8001", "NEXT_PUBLIC_API_URL": ""}),
        (
            "agro.env",
            {"AGRO_API_INTERNAL_ORIGIN": "http://127.0.0.1:8001", "NEXT_PUBLIC_API_URL": ""},
        ),
    ):
        target = root / "config" / name
        target.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
        target.chmod(0o600)
    say(f"Configuração sintética criada em {root}; segredos não exibidos.")
    say(
        f"Crie manualmente o database {dbname} e role de aplicação {user} na instância dedicada "
        "127.0.0.1:5433; a role migradora é provisionada separadamente por database."
    )
    say("Nenhum serviço foi iniciado e nenhum database foi alterado.")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    validate_all(args.root)
    for binary in ("psql", "pg_isready", "redis-cli", "node", "pnpm"):
        if not shutil_which(binary):
            raise GateError(f"Pré-requisito ausente: {binary}.")
    if not (ROOT / "services/api/.venv/bin/uvicorn").is_file():
        raise GateError("Uvicorn do ambiente virtual da API não está instalado.")
    say("Gate de configuração aprovado; ferramentas presentes.")
    say("Gate não prova identidade dos serviços nem aprovação Alembic.")
    return 0


def shutil_which(name: str) -> str | None:
    from shutil import which

    return which(name)


def cmd_identity(args: argparse.Namespace) -> int:
    apis, _, _ = validate_all(args.root)
    env = apis[0]
    parsed = urlparse(env["DATABASE_URL"])
    dbpass = parsed.password or ""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as pgpass:
        os.chmod(pgpass.name, 0o600)
        pgpass.write(f"127.0.0.1:5433:{parsed.path.lstrip('/')}:{parsed.username}:{dbpass}\n")
    try:
        psql = shutil_which("psql")
        redis_cli = shutil_which("redis-cli")
        if not psql or not redis_cli:
            raise GateError("psql e redis-cli são necessários para verificar identidade.")
        proc_env = dict(
            os.environ,
            PGPASSFILE=pgpass.name,
            REDISCLI_AUTH=urlparse(env["REDIS_URL"]).password or "",
        )
        query = (
            "SELECT current_database(), current_user, inet_server_addr()::text, inet_server_port()"
        )
        result = subprocess.run(  # noqa: S603
            [
                psql,
                "-X",
                "-h",
                "127.0.0.1",
                "-p",
                "5433",
                "-U",
                parsed.username or "",
                "-d",
                parsed.path.lstrip("/"),
                "-At",
                "-F",
                "|",
                "-c",
                query,
            ],
            env=proc_env,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            raise GateError("PostgreSQL dedicado não respondeu à verificação de identidade.")
        fields = result.stdout.strip().split("|")
        if (
            len(fields) != 4
            or fields[0] != parsed.path.lstrip("/")
            or fields[1] != parsed.username
            or fields[3] != "5433"
            or not is_exact_loopback_server_address(fields[2])
        ):
            raise GateError("Identidade PostgreSQL divergente; destino efetivo não comprovado.")
        redis = subprocess.run(  # noqa: S603
            [
                redis_cli,
                "-h",
                "127.0.0.1",
                "-p",
                "6380",
                "-n",
                "0",
                "GET",
                f"deepfarms:hml:{env['STAGING_INSTANCE_ID']}:identity",
            ],
            env=proc_env,
            text=True,
            capture_output=True,
        )
        if redis.returncode or redis.stdout.strip() != env["STAGING_INSTANCE_ID"]:
            raise GateError(
                "Redis não comprovou o marcador de identidade previamente provisionado."
            )
        say("PostgreSQL e Redis responderam e os identificadores conferem.")
        return 0
    finally:
        Path(pgpass.name).unlink(missing_ok=True)


def is_exact_loopback_server_address(value: str) -> bool:
    """Accept only exact IPv4/IPv6 loopback addresses, with full-width masks."""
    try:
        interface = ipaddress.ip_interface(value)
    except ValueError:
        return False
    if interface.ip == ipaddress.IPv4Address("127.0.0.1"):
        return interface.network.prefixlen == 32
    if interface.ip == ipaddress.IPv6Address("::1"):
        return interface.network.prefixlen == 128
    return False


def expected_migration_role(instance_id: str, database_name: str) -> str:
    """Return a collision-resistant migration role unique to one lab database."""
    lab = re.sub(r"[^a-z0-9]", "", instance_id.lower())[:10]
    db_slug = re.sub(r"[^a-z0-9]", "", database_name.lower())[:20]
    db_digest = hashlib.sha256(f"{instance_id}:{database_name}".encode("utf-8")).hexdigest()[:16]
    return f"agro_hml_mig_{lab}_{db_slug}_{db_digest}"


APPROVAL_FIELDS = {"instance_id", "database", "revision", "authorization_id"}


def _is_exact_revision(value: object) -> bool:
    return isinstance(value, str) and bool(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value)
    ) and value.lower() not in {"head", "heads", "base"}


def validate_migration_approval(
    root: Path, api_env: dict[str, str], requested_revision: str | None = None
) -> dict[str, str]:
    """Require a private, exact database/revision authorization record."""
    path = root / "config" / "migration-approval.json"
    try:
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise GateError("Autorização de migration precisa ter modo 0600.")
        approval = json.loads(path.read_text(encoding="utf-8"))
    except GateError:
        raise
    except (OSError, json.JSONDecodeError):
        raise GateError("Autorização explícita de migration ausente ou inválida.") from None
    if not isinstance(approval, dict) or set(approval) != APPROVAL_FIELDS:
        raise GateError("Autorização de migration tem formato inválido.")
    db = urlparse(api_env["DATABASE_URL"])
    target_database = (db.path or "").lstrip("/")
    if (
        approval.get("instance_id") != api_env["STAGING_INSTANCE_ID"]
        or approval.get("database") != target_database
        or not _is_exact_revision(approval.get("revision"))
        or not isinstance(approval.get("authorization_id"), str)
        or not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{7,79}", approval["authorization_id"])
    ):
        raise GateError("Autorização não corresponde ao laboratório, database ou revisão exata.")
    if requested_revision is not None:
        if not _is_exact_revision(requested_revision):
            raise GateError("Solicitação precisa indicar uma revisão exata, sem head/heads/base ou ranges.")
        if approval["revision"] != requested_revision:
            raise GateError("Revisão solicitada diverge da revisão explicitamente autorizada.")
    return approval


def validate_migration_env(root: Path, api_env: dict[str, str]) -> tuple[dict[str, str], object]:
    """Validate a private migration DSN bound to this lab's synthetic API config."""
    path = root / "config" / "alembic-migration.env"
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        raise GateError("Configuração privada Alembic ausente ou inacessível.") from None
    if mode != 0o600:
        raise GateError("Configuração privada Alembic precisa ter modo 0600.")
    values = read_env(path)
    if set(values) != set(api_env):
        raise GateError("Env Alembic deve conter exatamente as chaves sintéticas do laboratório.")
    if any(values[key] != api_env[key] for key in values if key != "DATABASE_URL"):
        raise GateError("Env Alembic diverge das configurações sintéticas do laboratório.")
    if values.get("ENVIRONMENT") != "staging" or values.get("APP_ENV") != "staging":
        raise GateError("Env Alembic precisa manter ENVIRONMENT/APP_ENV staging.")
    if values.get("STAGING_INSTANCE_ID") != api_env.get("STAGING_INSTANCE_ID"):
        raise GateError("ID do env Alembic diverge do laboratório.")

    api_db = urlparse(api_env["DATABASE_URL"])
    db = urlparse(values["DATABASE_URL"])
    expected_db = (api_db.path or "").lstrip("/")
    expected_role = expected_migration_role(api_env["STAGING_INSTANCE_ID"], expected_db)
    if (
        db.scheme != "postgresql+asyncpg"
        or db.hostname != "127.0.0.1"
        or db.port != 5433
        or (db.path or "").lstrip("/") != expected_db
        or db.username != expected_role
        or db.username in {api_db.username, ""}
        or not db.password
        or len(unquote(db.password)) < 32
        or db.query
        or db.fragment
    ):
        raise GateError("DATABASE_URL Alembic não corresponde ao role/database exclusivos do laboratório.")
    return values, db


def validate_migration_identity_record(record: dict[str, object], api_env: dict[str, str]) -> bool:
    """Validate the effective PostgreSQL identity and least-privilege evidence."""
    api_db = urlparse(api_env["DATABASE_URL"])
    expected_db = (api_db.path or "").lstrip("/")
    expected_role = expected_migration_role(api_env["STAGING_INSTANCE_ID"], expected_db)
    if (
        record.get("database") != expected_db
        or record.get("session_user") != expected_role
        or record.get("current_user") != expected_role
        or not is_exact_loopback_server_address(str(record.get("address", "")))
        or record.get("port") != 5433
        or record.get("can_login") is not True
        or record.get("superuser") is not False
        or record.get("createdb") is not False
        or record.get("createrole") is not False
        or record.get("replication") is not False
        or record.get("bypassrls") is not False
        or record.get("inherit") is not False
        or record.get("database_owner") is not False
        or record.get("target_connect") is not True
        or record.get("target_create") is not True
        or record.get("target_temp") is not False
        or record.get("database_owner_role")
        != "agro_hml_owner_"
        + re.sub(r"[^a-z0-9]", "", api_env["STAGING_INSTANCE_ID"].lower())[:12]
        or record.get("membership_count") != 0
        or record.get("app_target_connect") is not True
        or record.get("app_target_create") is not False
        or record.get("app_target_temp") is not False
        or record.get("app_migration_membership") is not False
        or record.get("admin_attributes_preserved") is not True
    ):
        return False
    other = record.get("other_databases")
    return isinstance(other, list) and all(
        isinstance(item, dict)
        and item.get("connect") is False
        and item.get("create") is False
        and item.get("temp") is False
        for item in other
    )


def cmd_migration_identity(args: argparse.Namespace) -> int:
    apis, _, _ = validate_all(args.root)
    _, db = validate_migration_env(args.root, apis[0])
    psql = shutil_which("psql")
    if not psql:
        raise GateError("psql é necessário para verificar a role de migração.")
    password = unquote(db.password or "")
    username = db.username or ""
    database = (db.path or "").lstrip("/")
    databases = [database, "postgres", "template0", "template1"]
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as pgpass:
        os.chmod(pgpass.name, 0o600)
        for dbname in dict.fromkeys(databases):
            pgpass.write(f"127.0.0.1:5433:{dbname}:{username}:{password}\n")
    try:
        proc_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", str(Path.home())),
            "LANG": os.environ.get("LANG", "C"),
            "PGPASSFILE": pgpass.name,
            "PGCONNECT_TIMEOUT": "5",
        }
        instance_id = apis[0]["STAGING_INSTANCE_ID"].lower()
        suffix = re.sub(r"[^a-z0-9]", "", instance_id)[:12]
        admin_role = "agro_hml_owner_" + suffix
        app_role = urlparse(apis[0]["DATABASE_URL"]).username or ""
        query = f"""
            SELECT json_build_object(
              'database', current_database(),
              'session_user', session_user,
              'current_user', current_user,
              'address', inet_server_addr()::text,
              'port', inet_server_port(),
              'can_login', r.rolcanlogin,
              'superuser', r.rolsuper,
              'createdb', r.rolcreatedb,
              'createrole', r.rolcreaterole,
              'replication', r.rolreplication,
              'bypassrls', r.rolbypassrls,
              'inherit', r.rolinherit,
              'database_owner', d.datdba = r.oid,
              'database_owner_role', pg_get_userbyid(d.datdba),
              'target_connect', has_database_privilege(r.oid, d.oid, 'CONNECT'),
              'target_create', has_database_privilege(r.oid, d.oid, 'CREATE'),
              'target_temp', has_database_privilege(r.oid, d.oid, 'TEMP'),
              'membership_count', (SELECT count(*) FROM pg_auth_members m
                                   WHERE m.member = r.oid OR m.roleid = r.oid),
              'other_databases', (SELECT COALESCE(json_agg(json_build_object(
                    'database', x.datname,
                    'connect', has_database_privilege(r.oid, x.oid, 'CONNECT'),
                    'create', has_database_privilege(r.oid, x.oid, 'CREATE'),
                    'temp', has_database_privilege(r.oid, x.oid, 'TEMP')
                  ) ORDER BY x.datname), '[]'::json)
                  FROM pg_database x WHERE x.oid <> d.oid),
              'app_target_connect', has_database_privilege(a.oid, d.oid, 'CONNECT'),
              'app_target_create', has_database_privilege(a.oid, d.oid, 'CREATE'),
              'app_target_temp', has_database_privilege(a.oid, d.oid, 'TEMP'),
              'app_migration_membership', EXISTS (SELECT 1 FROM pg_auth_members m
                  WHERE (m.member = a.oid AND m.roleid = r.oid)
                     OR (m.member = r.oid AND m.roleid = a.oid)),
              'admin_attributes_preserved', (SELECT rolsuper AND rolcreatedb
                  AND rolcreaterole AND rolreplication AND rolbypassrls
                  FROM pg_roles WHERE rolname = '{admin_role}')
            )::text
            FROM pg_roles r
            JOIN pg_database d ON d.datname = current_database()
            JOIN pg_roles a ON a.rolname = '{app_role}'
            WHERE r.rolname = current_user
        """
        result = subprocess.run(  # noqa: S603
            [psql, "-X", "-h", "127.0.0.1", "-p", "5433", "-U", username,
             "-d", database, "-At", "-c", query],
            env=proc_env,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            raise GateError("Role de migração não autenticou no database do laboratório.")
        try:
            record = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            raise GateError("Resposta de identidade da role de migração inválida.") from None
        if not validate_migration_identity_record(record, apis[0]):
            raise GateError("Privilégios efetivos da role de migração excedem o escopo aprovado.")

        for denied_db in ("postgres", "template1"):
            denied = subprocess.run(  # noqa: S603
                [psql, "-X", "-h", "127.0.0.1", "-p", "5433", "-U", username,
                 "-d", denied_db, "-At", "-c", "SELECT current_database()"],
                env=proc_env,
                text=True,
                capture_output=True,
            )
            if denied.returncode == 0 or "permission denied for database" not in denied.stderr.lower():
                raise GateError("Conexão da role de migração não foi negada em database não autorizado.")
        template0 = subprocess.run(  # noqa: S603
            [psql, "-X", "-h", "127.0.0.1", "-p", "5433", "-U", username,
             "-d", "template0", "-At", "-c", "SELECT current_database()"],
            env=proc_env,
            text=True,
            capture_output=True,
        )
        if template0.returncode == 0 or "not currently accepting connections" not in template0.stderr.lower():
            raise GateError("Conexão da role de migração não foi negada em template0.")
        say("Role Alembic autenticada; privilégios e databases não autorizados conferem.")
        return 0
    finally:
        Path(pgpass.name).unlink(missing_ok=True)


def child_env(config: dict[str, str], root: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        if (
            re.search(
                r"(API_KEY|ACCESS_KEY|CLIENT_SECRET|WEBHOOK_SECRET|_TOKEN$|TOKEN$|SECRET_KEY|SMTP_PASS|MAIL_PASS)",
                key,
            )
            and key not in INTERNAL_SECRETS
        ) or key in {
            "BACKEND_URL",
            "AGRO_API_INTERNAL_ORIGIN",
            "NEXT_PUBLIC_API_URL",
            "NEXT_PUBLIC_WS_URL",
        }:
            env.pop(key, None)
    env.update({k: v for k, v in config.items() if not k.startswith("_")})
    env["PYTHONPATH"] = str(ROOT / "services" / "api") + os.pathsep + env.get("PYTHONPATH", "")
    return env


def frontend_env(config: dict[str, str]) -> dict[str, str]:
    # Next only receives basic host process settings and its explicitly vetted
    # local origins; application and provider secrets are not inherited.
    env = {
        key: os.environ[key]
        for key in ("PATH", "HOME", "USER", "LOGNAME", "LANG", "TMPDIR", "CI")
        if key in os.environ
    }
    env.update({key: value for key, value in config.items() if not key.startswith("_")})
    env["NODE_ENV"] = "development"
    return env


def launch(root: Path, key: str, command: list[str], env: dict[str, str]) -> None:
    run_dir = root / "run"
    log_path = root / "logs" / f"{key}.log"
    pid_path = run_dir / f"{key}.pid"
    if pid_path.exists():
        raise GateError(f"PID file já existe para {key}; inspeção manual necessária.")
    log = open(log_path, "ab", buffering=0)
    proc = subprocess.Popen(  # noqa: S603
        command,
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pid_path.write_text(str(proc.pid), encoding="ascii")
    pid_path.chmod(0o600)
    say(f"Iniciado {key}, PID {proc.pid}; log em {log_path}.")


def cmd_start(args: argparse.Namespace) -> int:
    raise GateError(
        "BLOCKER Alembic: inicialização bloqueada até haver uma revisão de banco vazio "
        "aprovada e registrada no controlador."
    )


def _cmd_start_after_migration_approval(args: argparse.Namespace) -> int:
    """Prepared launcher; keep unreachable until Alembic target is approved."""
    apis, web, agro = validate_all(args.root)
    if args.component == "api1":
        ensure_port_free(8001)
        cmd_gate(argparse.Namespace(root=args.root))
        cmd_identity(argparse.Namespace(root=args.root))
        command = [
            str(ROOT / "services/api/.venv/bin/uvicorn"),
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ]
        launch(args.root, "api1", command, child_env(apis[0], args.root))
    elif args.component == "api2":
        ensure_port_free(8002)
        cmd_gate(argparse.Namespace(root=args.root))
        cmd_identity(argparse.Namespace(root=args.root))
        command = [
            str(ROOT / "services/api/.venv/bin/uvicorn"),
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8002",
        ]
        launch(args.root, "api2", command, child_env(apis[1], args.root))
    elif args.component == "web":
        ensure_port_free(3001)
        cmd_gate(argparse.Namespace(root=args.root))
        cmd_identity(argparse.Namespace(root=args.root))
        command = [
            "pnpm",
            "--dir",
            "apps/web",
            "exec",
            "next",
            "dev",
            "--webpack",
            "--hostname",
            "127.0.0.1",
            "--port",
            "3001",
        ]
        launch(args.root, "web", command, frontend_env(web))
    else:
        ensure_port_free(3005)
        cmd_gate(argparse.Namespace(root=args.root))
        cmd_identity(argparse.Namespace(root=args.root))
        command = [
            "pnpm",
            "--dir",
            "apps/agro",
            "exec",
            "next",
            "dev",
            "--webpack",
            "--hostname",
            "127.0.0.1",
            "--port",
            "3005",
        ]
        launch(args.root, "agro", command, frontend_env(agro))
    return 0


def ensure_port_free(port: int) -> None:
    with socket.socket() as sock:
        sock.settimeout(0.2)
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise GateError(f"Porta {port} já está ocupada; nenhum processo encerrado.")


def cmd_smoke(args: argparse.Namespace) -> int:
    for url in (
        "http://127.0.0.1:8001/health/live",
        "http://127.0.0.1:8002/health/live",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3005",
    ):
        try:
            with urlopen(url, timeout=2) as response:  # noqa: S310 -- URLs são literais loopback.
                if response.status >= 400:
                    raise GateError(f"Smoke falhou em {url}.")
        except Exception as exc:
            raise GateError(f"Smoke sem resposta em {url} ({type(exc).__name__}).") from None
    say("Smoke HTTP respondeu em todos os quatro processos.")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    run_dir = args.root / "run"
    for pid_file in sorted(run_dir.glob("*.pid")):
        try:
            pid = int(pid_file.read_text(encoding="ascii").strip())
            cmdline = (
                Path(f"/proc/{pid}/cmdline")
                .read_bytes()
                .replace(b"\0", b" ")
                .decode(errors="replace")
            )
        except (OSError, ValueError):
            pid_file.unlink(missing_ok=True)
            continue
        expected = "main:app" if pid_file.stem.startswith("api") else "next dev"
        if expected not in cmdline:
            raise GateError(
                f"PID registrado para {pid_file.stem} não corresponde ao comando esperado; "
                "nenhum sinal enviado."
            )
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        say(f"SIGTERM enviado ao processo {pid} ({pid_file.stem}).")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    # Run the official least-privilege gate before any migration-related action.
    # The lab migration path remains disabled until the historical graph is approved.
    cmd_migration_identity(args)
    apis, _, _ = validate_all(args.root)
    requested_revision = getattr(args, "revision", None)
    if not _is_exact_revision(requested_revision):
        raise GateError("Informe uma revisão Alembic exata; head/heads/base não são aceitos.")
    validate_migration_approval(args.root, apis[0], requested_revision)
    raise GateError(
        "BLOCKER Alembic: caminho baseline@head contém revisão histórica incompatível com --sql; "
        "não há execução liberada nesta fase. Requer decisão arquitetural e autorização "
        "posterior, mesmo com identidade e revisão aprovadas."
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name, func in (
        ("prepare", cmd_prepare),
        ("gate", cmd_gate),
        ("identity", cmd_identity),
        ("migration-identity", cmd_migration_identity),
        ("smoke", cmd_smoke),
        ("stop", cmd_stop),
        ("migrate", cmd_migrate),
    ):
        q = sub.add_parser(name)
        q.add_argument("--root", type=Path, required=True)
        if name == "migrate":
            q.add_argument(
                "--revision", required=True,
                help="Revisão exata registrada na autorização privada.",
            )
        q.set_defaults(func=func)
    q = sub.add_parser("start")
    q.add_argument("--root", type=Path, required=True)
    q.add_argument("component", choices=("api1", "api2", "web", "agro"))
    q.set_defaults(func=cmd_start)
    return p


if __name__ == "__main__":
    try:
        args = parser().parse_args()
        sys.exit(args.func(args))
    except GateError as exc:
        print(f"NO-GO: {exc}", file=sys.stderr)
        sys.exit(2)
