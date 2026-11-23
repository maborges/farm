from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("agro_labctl.py")
SPEC = importlib.util.spec_from_file_location("agro_labctl", MODULE_PATH)
labctl = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(labctl)

GUARD_PATH = Path(__file__).with_name("agro_lab_migration_guard.py")
GUARD_SPEC = importlib.util.spec_from_file_location("agro_lab_migration_guard", GUARD_PATH)
guard = importlib.util.module_from_spec(GUARD_SPEC)
assert GUARD_SPEC and GUARD_SPEC.loader
GUARD_SPEC.loader.exec_module(guard)

PROVISION_PATH = Path(__file__).with_name("provision_migration_identity.py")
PROVISION_SPEC = importlib.util.spec_from_file_location("provision_migration_identity", PROVISION_PATH)
provision = importlib.util.module_from_spec(PROVISION_SPEC)
assert PROVISION_SPEC and PROVISION_SPEC.loader
PROVISION_SPEC.loader.exec_module(provision)


def write_env(path: Path, values: dict[str, str]) -> Path:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    return path


def api_config(root: Path) -> dict[str, str]:
    values = {key: "" for key in labctl.local_env_keys()}
    values.update(
        {
            "ENVIRONMENT": "staging",
            "APP_ENV": "staging",
            "DATABASE_URL": "postgresql+asyncpg://lab_user:synthetic-secret@127.0.0.1:5433/agro_hml_case01",
            "REDIS_URL": "redis://:synthetic-redis-secret@127.0.0.1:6380/0",
            "STORAGE_BACKEND": "local",
            "STORAGE_LOCAL_PATH": str(root / "uploads"),
            "JWT_SECRET_KEY": "test-" + "a" * 48,
            "PLATFORM_CREDENTIALS_MASTER_KEY": "dGVzdC1rZXktZm9yLWxvY2FsLWhvbW9sb2dhY2FvLTAx",
            "INTEGRATIONS_SECRET_KEY": "test-" + "b" * 48,
            "STAGING_INSTANCE_ID": "case01x",
            "FRONTEND_URL": "http://127.0.0.1:3005",
            "ALLOW_ORIGINS": '["http://127.0.0.1:3001","http://127.0.0.1:3005"]',
        }
    )
    return values


def test_gate_accepts_only_explicit_isolated_loopback_configuration(tmp_path: Path) -> None:
    (tmp_path / "uploads").mkdir()
    config = tmp_path / "config"
    config.mkdir()
    first = api_config(tmp_path)
    second = dict(first, WORKER_ID="worker-2")
    write_env(config / "api1.env", first)
    write_env(config / "api2.env", second)
    (config / "manifest.json").write_text(
        json.dumps(
            {
                "instance_id": first["STAGING_INSTANCE_ID"],
                "secret_sha256": {
                    key: hashlib.sha256(first[key].encode()).hexdigest()
                    for key in (
                        "JWT_SECRET_KEY",
                        "PLATFORM_CREDENTIALS_MASTER_KEY",
                        "INTEGRATIONS_SECRET_KEY",
                    )
                },
            }
        ),
        encoding="utf-8",
    )
    write_env(config / "web.env", {"BACKEND_URL": "http://127.0.0.1:8001"})
    write_env(config / "agro.env", {"AGRO_API_INTERNAL_ORIGIN": "http://127.0.0.1:8001"})

    apis, _, _ = labctl.validate_all(tmp_path)

    assert apis[0]["DATABASE_URL"] == apis[1]["DATABASE_URL"]
    assert apis[0]["REDIS_URL"] == apis[1]["REDIS_URL"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("DATABASE_URL", "postgresql+asyncpg://u:p@prod-db.example:5432/app"),
        ("DATABASE_URL", "sqlite+aiosqlite:///./fallback.db"),
        ("REDIS_URL", "redis://:pw@10.0.0.2:6379/0"),
        ("STORAGE_BACKEND", "s3"),
        ("S3_ENDPOINT_URL", "http://127.0.0.1:9000"),
        ("WEATHERAPI_API_KEY", "real-or-unknown-provider-secret"),
    ],
)
def test_gate_rejects_unsafe_api_targets_and_external_credentials(
    tmp_path: Path, key: str, value: str
) -> None:
    (tmp_path / "uploads").mkdir()
    values = api_config(tmp_path)
    values[key] = value
    path = write_env(tmp_path / "api.env", values)

    with pytest.raises(labctl.GateError):
        labctl.validate_api_env(path, tmp_path)


def test_gate_rejects_frontend_origin_outside_lab(tmp_path: Path) -> None:
    path = write_env(tmp_path / "web.env", {"BACKEND_URL": "https://api.deepfarms.com.br"})

    with pytest.raises(labctl.GateError):
        labctl.validate_front_env(path, "web")


def test_process_environment_overrides_api_local_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from core.config import Settings

    synthetic_url = "postgresql+asyncpg://test:test@127.0.0.1:5433/agro_hml_envtest"
    monkeypatch.setenv("DATABASE_URL", synthetic_url)
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    storage_path = str(tmp_path / "uploads")
    monkeypatch.setenv("STORAGE_LOCAL_PATH", storage_path)

    settings = Settings()

    assert settings.database_url == synthetic_url
    assert settings.storage_backend == "local"
    assert settings.storage_local_path == storage_path


def test_migration_command_fails_closed_while_graph_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    called = []
    monkeypatch.setattr(labctl, "cmd_migration_identity", lambda args: called.append(args.root) or 0)
    monkeypatch.setattr(labctl, "validate_all", lambda _root: ([api_config(Path("/tmp/lab"))], {}, {}))
    monkeypatch.setattr(labctl, "validate_migration_approval", lambda *_args: {})
    with pytest.raises(labctl.GateError, match="BLOCKER Alembic"):
        labctl.cmd_migrate(SimpleNamespace(root=Path("/tmp/lab"), revision="baseline_deepfarms_v1"))
    assert called == [Path("/tmp/lab")]


def test_migrate_stops_when_official_identity_gate_is_no_go(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    def reject(_args):
        raise labctl.GateError("official gate NO-GO")

    monkeypatch.setattr(labctl, "cmd_migration_identity", reject)
    with pytest.raises(labctl.GateError, match="official gate NO-GO"):
        labctl.cmd_migrate(SimpleNamespace(root=Path("/tmp/lab"), revision="baseline_deepfarms_v1"))


def test_start_command_fails_closed_until_migration_target_is_approved() -> None:
    with pytest.raises(labctl.GateError, match="inicialização bloqueada"):
        labctl.cmd_start(object())


def test_frontend_environment_drops_inherited_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "do-not-forward")
    monkeypatch.setenv("JWT_SECRET_KEY", "do-not-forward-either")

    env = labctl.frontend_env({"BACKEND_URL": "http://127.0.0.1:8001"})

    assert "ANTHROPIC_API_KEY" not in env
    assert "JWT_SECRET_KEY" not in env
    assert env["BACKEND_URL"] == "http://127.0.0.1:8001"


@pytest.mark.parametrize("address", ["127.0.0.1", "127.0.0.1/32", "::1", "::1/128"])
def test_identity_accepts_only_exact_loopback_addresses(address: str) -> None:
    assert labctl.is_exact_loopback_server_address(address)


@pytest.mark.parametrize(
    "address",
    ["127.0.0.2", "127.0.0.1/24", "::2", "::1/64", "10.0.0.1", "invalid"],
)
def test_identity_rejects_non_exact_loopback_addresses(address: str) -> None:
    assert not labctl.is_exact_loopback_server_address(address)


def write_migration_env(root: Path, api_values: dict[str, str], database_url: str | None = None) -> Path:
    config = root / "config"
    config.mkdir(exist_ok=True)
    values = dict(api_values)
    if database_url is not None:
        values["DATABASE_URL"] = database_url
    path = write_env(config / "alembic-migration.env", values)
    path.chmod(0o600)
    return path


def test_migration_env_is_bound_to_a_distinct_synthetic_role_and_exact_lab_target(
    tmp_path: Path,
) -> None:
    api_values = api_config(tmp_path)
    role = labctl.expected_migration_role(api_values["STAGING_INSTANCE_ID"], "agro_hml_case01")
    write_migration_env(
        tmp_path,
        api_values,
        f"postgresql+asyncpg://{role}:synthetic-migration-secret-long-enough@127.0.0.1:5433/agro_hml_case01",
    )

    values, parsed = labctl.validate_migration_env(tmp_path, api_values)

    assert values["DATABASE_URL"] == parsed.geturl()
    assert parsed.username == role
    assert parsed.username != "lab_user"


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://agro_hml_migrate_case01x:synthetic-migration-secret-long-enough@192.168.0.2:5433/agro_hml_case01",
        "postgresql+asyncpg://agro_hml_migrate_case01x:synthetic-migration-secret-long-enough@127.0.0.1:5433/farms",
        "postgresql+asyncpg://lab_user:synthetic-migration-secret-long-enough@127.0.0.1:5433/agro_hml_case01",
        "postgresql+asyncpg://agro_hml_owner_case01x:synthetic-migration-secret-long-enough@127.0.0.1:5433/agro_hml_case01",
    ],
)
def test_migration_env_rejects_wrong_target_or_privileged_role(
    tmp_path: Path, database_url: str
) -> None:
    api_values = api_config(tmp_path)
    write_migration_env(tmp_path, api_values, database_url)

    with pytest.raises(labctl.GateError):
        labctl.validate_migration_env(tmp_path, api_values)


def test_migration_env_requires_private_permissions(tmp_path: Path) -> None:
    api_values = api_config(tmp_path)
    role = labctl.expected_migration_role(api_values["STAGING_INSTANCE_ID"], "agro_hml_case01")
    path = write_migration_env(
        tmp_path,
        api_values,
        f"postgresql+asyncpg://{role}:synthetic-migration-secret-long-enough@127.0.0.1:5433/agro_hml_case01",
    )
    path.chmod(0o640)

    with pytest.raises(labctl.GateError, match="modo 0600"):
        labctl.validate_migration_env(tmp_path, api_values)


def migration_identity_record() -> dict[str, object]:
    return {
        "database": "agro_hml_case01",
        "session_user": labctl.expected_migration_role("case01x", "agro_hml_case01"),
        "current_user": labctl.expected_migration_role("case01x", "agro_hml_case01"),
        "address": "127.0.0.1/32",
        "port": 5433,
        "can_login": True,
        "superuser": False,
        "createdb": False,
        "createrole": False,
        "replication": False,
        "bypassrls": False,
        "inherit": False,
        "database_owner": False,
        "database_owner_role": "agro_hml_owner_case01x",
        "target_connect": True,
        "target_create": True,
        "target_temp": False,
        "membership_count": 0,
        "other_databases": [
            {"database": "postgres", "connect": False, "create": False, "temp": False},
            {"database": "template1", "connect": False, "create": False, "temp": False},
        ],
        "app_target_connect": True,
        "app_target_create": False,
        "app_target_temp": False,
        "app_migration_membership": False,
        "admin_attributes_preserved": True,
    }


def test_migration_identity_gate_requires_scoped_privileges() -> None:
    api_values = api_config(Path("/tmp/case01"))

    assert labctl.validate_migration_identity_record(migration_identity_record(), api_values)

    for key, unsafe in (
        ("superuser", True),
        ("createdb", True),
        ("createrole", True),
        ("replication", True),
        ("bypassrls", True),
        ("target_create", False),
        ("target_temp", True),
        ("membership_count", 1),
        ("app_target_create", True),
        ("admin_attributes_preserved", False),
    ):
        record = migration_identity_record()
        record[key] = unsafe
        assert not labctl.validate_migration_identity_record(record, api_values)

    record = migration_identity_record()
    record["other_databases"] = [
        {"database": "postgres", "connect": True, "create": False, "temp": False}
    ]
    assert not labctl.validate_migration_identity_record(record, api_values)


def test_migration_roles_are_unique_per_database() -> None:
    first = labctl.expected_migration_role("dbdcc24872aa2992", "agro_hml_dbdcc24872aa")
    second = labctl.expected_migration_role("dbdcc24872aa2992", "agro_hml_dbdcc24872aa_d3d")
    assert first != second
    assert len(first) <= 63
    assert len(second) <= 63


def test_legacy_shared_migration_role_is_not_valid_for_database_bound_env(tmp_path: Path) -> None:
    api_values = api_config(tmp_path)
    legacy_role = "agro_hml_migrate_case01x"
    write_migration_env(
        tmp_path,
        api_values,
        f"postgresql+asyncpg://{legacy_role}:synthetic-migration-secret-long-enough@127.0.0.1:5433/agro_hml_case01",
    )
    with pytest.raises(labctl.GateError, match="role/database exclusivos"):
        labctl.validate_migration_env(tmp_path, api_values)


def test_migration_approval_binds_instance_database_and_revision(tmp_path: Path) -> None:
    values = api_config(tmp_path)
    config = tmp_path / "config"
    config.mkdir()
    approval = {
        "instance_id": values["STAGING_INSTANCE_ID"],
        "database": "agro_hml_case01",
        "revision": "baseline_deepfarms_v1",
        "authorization_id": "AGRO-ADMIN-TEST-0001",
    }
    path = config / "migration-approval.json"
    path.write_text(json.dumps(approval), encoding="utf-8")
    path.chmod(0o600)

    assert labctl.validate_migration_approval(tmp_path, values, "baseline_deepfarms_v1") == approval
    with pytest.raises(labctl.GateError, match="revisão exata"):
        labctl.validate_migration_approval(tmp_path, values, "head")
    path.chmod(0o640)
    with pytest.raises(labctl.GateError, match="0600"):
        labctl.validate_migration_approval(tmp_path, values)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("instance_id", "another-lab"),
        ("database", "farms"),
        ("revision", "head"),
        ("authorization_id", "bad id"),
    ],
)
def test_migration_approval_rejects_wrong_binding_or_invalid_fields(
    tmp_path: Path, field: str, bad_value: str
) -> None:
    values = api_config(tmp_path)
    config = tmp_path / "config"
    config.mkdir()
    approval = {
        "instance_id": values["STAGING_INSTANCE_ID"],
        "database": "agro_hml_case01",
        "revision": "deepfarms_clean_install_v1",
        "authorization_id": "AGRO-ADMIN-TEST-0001",
    }
    approval[field] = bad_value
    path = config / "migration-approval.json"
    path.write_text(json.dumps(approval), encoding="utf-8")
    path.chmod(0o600)

    with pytest.raises(labctl.GateError):
        labctl.validate_migration_approval(tmp_path, values, "deepfarms_clean_install_v1")


def test_migration_approval_rejects_missing_file(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    with pytest.raises(labctl.GateError, match="ausente ou inválida"):
        labctl.validate_migration_approval(tmp_path, api_config(tmp_path), "deepfarms_clean_install_v1")


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://u:p@127.0.0.1:5433/agro_hml_x",
        "postgresql://u:p@localhost:5433/deepfarms_staging_x",
    ],
)
def test_alembic_guard_recognizes_local_lab_targets(url: str) -> None:
    assert guard.is_lab_migration_target(url, {})


def test_alembic_guard_recognizes_staging_database_on_lab_port() -> None:
    assert guard.is_lab_migration_target(
        "postgresql+asyncpg://u:p@127.0.0.1:5433/future_db",
        {"ENVIRONMENT": "staging"},
    )


def test_alembic_guard_fails_closed_without_lab_root(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    monkeypatch.delenv("AGRO_LAB_ROOT", raising=False)
    with pytest.raises(RuntimeError, match="AGRO_LAB_ROOT ausente"):
        guard.enforce_lab_migration_guard(
            "postgresql+asyncpg://role:secret@127.0.0.1:5433/agro_hml_x",
            SimpleNamespace(revision="baseline_deepfarms_v1"),
        )


@pytest.mark.parametrize("revision", [None, "head", "heads", "base", "base+head", "a,b"])
def test_alembic_guard_rejects_implicit_or_ranged_revision(revision: str | None) -> None:
    from types import SimpleNamespace

    with pytest.raises(RuntimeError):
        guard._requested_revision(SimpleNamespace(revision=revision))


def test_provisioner_ddl_grants_only_database_scope() -> None:
    sql = provision.build_role_ddl(
        "agro_hml_mig_lab_db_12345678", "synthetic-secret", "agro_hml_lab_db"
    )
    assert "LOGIN" in sql and "NOINHERIT" in sql
    assert all(flag in sql for flag in ("NOSUPERUSER", "NOCREATEDB", "NOCREATEROLE", "NOREPLICATION", "NOBYPASSRLS"))
    assert "REVOKE ALL ON DATABASE \"agro_hml_lab_db\" FROM PUBLIC" in sql
    assert "GRANT CONNECT, CREATE ON DATABASE \"agro_hml_lab_db\"" in sql
    assert "GRANT CONNECT, CREATE ON DATABASE \"postgres\"" not in sql
    assert "SUPERUSER" not in sql.replace("NOSUPERUSER", "")


def test_provisioner_quotes_password_as_sql_literal() -> None:
    sql = provision.build_role_ddl("agro_mig_lab_db_12345678", "x' OR true --", "agro_hml_lab_db")
    assert "PASSWORD 'x'' OR true --'" in sql
