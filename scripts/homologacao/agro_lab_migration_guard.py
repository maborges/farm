"""Fail-closed Alembic guard for the isolated local Agro homologation lab."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse


def is_lab_migration_target(database_url: str, environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    parsed = urlparse(database_url)
    database = (parsed.path or "").lstrip("/").lower()
    named_target = database.startswith(
        ("agro_hml_", "deepfarms_hml_", "agro_staging_", "deepfarms_staging_")
    )
    local_target = (
        parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and parsed.port == 5433
        and named_target
    )
    explicitly_staging = (
        env.get("ENVIRONMENT", "").lower() == "staging"
        and env.get("APP_ENV", "").lower() == "staging"
        and bool(env.get("STAGING_INSTANCE_ID"))
    )
    local_staging = (
        env.get("ENVIRONMENT", "").lower() == "staging"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and parsed.port == 5433
    )
    return named_target or local_target or explicitly_staging or local_staging


def _requested_revision(command_options: object | None) -> str:
    value = getattr(command_options, "revision", None)
    if isinstance(value, (tuple, list)):
        if len(value) != 1:
            raise RuntimeError("Laboratório exige exatamente uma revisão Alembic explícita.")
        value = value[0]
    if not isinstance(value, str) or not value or value.lower() in {"head", "heads", "base"}:
        raise RuntimeError("Laboratório exige uma revisão Alembic exata; head/heads/base são bloqueados.")
    if any(token in value for token in (",", "+", "-")):
        raise RuntimeError("Laboratório rejeita ranges e múltiplos alvos Alembic.")
    return value


def enforce_lab_migration_guard(
    database_url: str, command_options: object | None, alembic_config: object | None = None
) -> None:
    """Require target binding, explicit approval, and the official live identity gate."""
    if not is_lab_migration_target(database_url):
        return
    root_value = os.environ.get("AGRO_LAB_ROOT", "")
    if not root_value:
        raise RuntimeError("Migration do laboratório bloqueada: AGRO_LAB_ROOT ausente.")
    root = Path(root_value).resolve()
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "scripts" / "homologacao"))
    import agro_labctl  # pylint: disable=import-outside-toplevel

    try:
        api_envs, _, _ = agro_labctl.validate_all(root)
        migration_env, migration_db = agro_labctl.validate_migration_env(root, api_envs[0])
        requested = _requested_revision(command_options)
        approval = agro_labctl.validate_migration_approval(root, api_envs[0], requested)
        if alembic_config is None:
            raise agro_labctl.GateError("Configuração Alembic efetiva ausente para validar a revisão.")
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(alembic_config)
        if script.get_revision(requested) is None:
            raise agro_labctl.GateError("Revisão autorizada não existe no grafo Alembic do checkout.")
        active = urlparse(database_url)
        if (
            active.scheme != migration_db.scheme
            or active.hostname != migration_db.hostname
            or active.port != migration_db.port
            or (active.path or "").lstrip("/") != (migration_db.path or "").lstrip("/")
            or active.username != migration_db.username
            or active.password != migration_db.password
        ):
            raise agro_labctl.GateError("Alvo efetivo do Alembic diverge da configuração privada autorizada.")
        if approval["database"] != (active.path or "").lstrip("/"):
            raise agro_labctl.GateError("Autorização Alembic não corresponde ao database efetivo.")
        # This is the same command exposed to operators as `migration-identity`.
        agro_labctl.cmd_migration_identity(type("Args", (), {"root": root})())
    except agro_labctl.GateError as exc:
        raise RuntimeError(f"Migration do laboratório bloqueada pelo gate oficial: {exc}") from None

