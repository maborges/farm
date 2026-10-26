from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

API_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = API_ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "homologacao"))
sys.path.insert(0, str(API_ROOT))

spec = importlib.util.spec_from_file_location(
    "agro_clean_install_preflight", REPO_ROOT / "scripts/homologacao/agro_clean_install.py"
)
runner = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(runner)


@pytest.mark.parametrize("address", ["127.0.0.1", "127.0.0.1/32"])
def test_postgres_identity_accepts_exact_loopback_representations(address: str) -> None:
    runner._validate_database_identity(
        (runner.AUTHORIZED_DATABASE, "d3f_migrator", address, 5433), "d3f_migrator"
    )


@pytest.mark.parametrize(
    ("database", "role", "address", "port"),
    [
        (runner.AUTHORIZED_DATABASE, "d3f_migrator", "10.0.0.5", 5433),
        (runner.AUTHORIZED_DATABASE, "d3f_migrator", "127.0.0.2", 5433),
        (runner.AUTHORIZED_DATABASE, "d3f_migrator", "127.0.0.1/24", 5433),
        ("farms", "d3f_migrator", "127.0.0.1/32", 5433),
        (runner.AUTHORIZED_DATABASE, "wrong_role", "127.0.0.1/32", 5433),
        (runner.AUTHORIZED_DATABASE, "d3f_migrator", "127.0.0.1/32", 5432),
    ],
)
def test_postgres_identity_rejects_wrong_database_role_address_or_port(
    database: str, role: str, address: str, port: int
) -> None:
    with pytest.raises(runner.agro_labctl.GateError):
        runner._validate_database_identity((database, role, address, port), "d3f_migrator")


def test_postgres_identity_rejects_malformed_result() -> None:
    with pytest.raises(runner.agro_labctl.GateError, match="Resposta de identidade"):
        runner._validate_database_identity((runner.AUTHORIZED_DATABASE,), "d3f_migrator")


@pytest.mark.parametrize(
    ("schema_exists", "application_objects", "version_objects"),
    [(True, 0, (None, None)), (False, 2, (None, None)), (False, 0, ("farms.version", None))],
)
def test_database_preflight_rejects_schema_objects_or_version_tables(
    schema_exists: bool, application_objects: int, version_objects: tuple[object, ...]
) -> None:
    with pytest.raises(runner.agro_labctl.GateError):
        runner._validate_empty_database(
            schema_exists=schema_exists,
            application_objects=application_objects,
            version_objects=version_objects,
        )


def test_database_preflight_accepts_empty_database() -> None:
    runner._validate_empty_database(
        schema_exists=False, application_objects=0, version_objects=(None, None)
    )


def test_runner_preflight_fails_closed_on_hash_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import clean_install.manifest as manifest

    monkeypatch.setattr(runner, "AUTHORIZED_ROOT", tmp_path)
    monkeypatch.setattr(runner, "AUTHORIZED_DATABASE", "agro_hml_case01")
    api = {"DATABASE_URL": "postgresql+asyncpg://app:pw@127.0.0.1:5433/agro_hml_case01"}
    migration_url = "postgresql+asyncpg://mig:pw@127.0.0.1:5433/agro_hml_case01"
    monkeypatch.setattr(runner.agro_labctl, "validate_all", lambda _root: ([api], {}, {}))
    monkeypatch.setattr(
        runner.agro_labctl,
        "validate_migration_env",
        lambda _root, _api: ({"DATABASE_URL": migration_url}, urlparse(migration_url)),
    )
    monkeypatch.setattr(
        runner.agro_labctl,
        "validate_migration_approval",
        lambda *_args: {"database": "agro_hml_case01"},
    )

    def mismatch(_api_root: Path) -> dict[str, str]:
        raise RuntimeError("hash mismatch detail must not escape")

    monkeypatch.setattr(manifest, "verify_artifact_hashes", mismatch)
    with pytest.raises(runner.agro_labctl.GateError, match="Hashes fixados"):
        runner._preflight(tmp_path)


@pytest.mark.parametrize("failed_gate", ["identity", "migration_identity"])
def test_runner_never_reaches_installer_when_official_gate_fails(
    monkeypatch: pytest.MonkeyPatch, failed_gate: str, tmp_path: Path
) -> None:
    monkeypatch.setattr(runner, "_preflight", lambda _root: ({}, {}, {}))
    calls: list[str] = []
    identity_result = 1 if failed_gate == "identity" else 0
    migration_result = 1 if failed_gate == "migration_identity" else 0
    monkeypatch.setattr(
        runner.agro_labctl,
        "cmd_identity",
        lambda _args: calls.append("identity") or identity_result,
    )
    monkeypatch.setattr(
        runner.agro_labctl,
        "cmd_migration_identity",
        lambda _args: calls.append("migration_identity") or migration_result,
    )

    async def unexpected_install(*_args):
        calls.append("install")
        return {}

    monkeypatch.setattr(runner, "_execute_install", unexpected_install)
    with pytest.raises(runner.agro_labctl.GateError, match="Gate"):
        runner.run(tmp_path)
    assert "install" not in calls
    assert calls[0] == "identity"
    if failed_gate == "identity":
        assert calls == ["identity"]
    else:
        assert calls == ["identity", "migration_identity"]


def test_identity_gate_rejects_redis_authentication_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import agro_labctl

    api = {
        "DATABASE_URL": "postgresql+asyncpg://lab_user:synthetic@127.0.0.1:5433/agro_hml_case01",
        "REDIS_URL": "redis://:synthetic@127.0.0.1:6380/0",
        "STAGING_INSTANCE_ID": "case01x",
    }
    monkeypatch.setattr(agro_labctl, "validate_all", lambda _root: ([api], {}, {}))
    monkeypatch.setattr(agro_labctl, "shutil_which", lambda name: f"/fake/{name}")
    responses = iter(
        [
            subprocess.CompletedProcess([], 0, "agro_hml_case01|lab_user|127.0.0.1/32|5433\n", ""),
            subprocess.CompletedProcess([], 1, "", "NOAUTH Authentication required"),
        ]
    )
    monkeypatch.setattr(
        agro_labctl.subprocess,
        "run",
        lambda *_args, **_kwargs: next(responses),
    )
    with pytest.raises(agro_labctl.GateError, match="Redis não comprovou"):
        agro_labctl.cmd_identity(SimpleNamespace(root=tmp_path))


def test_runner_import_path_allows_clean_install_modules_without_prior_api_path() -> None:
    code = (
        "import importlib.util, runpy, sys; "
        f"sys.path.remove({str(API_ROOT)!r}) if {str(API_ROOT)!r} in sys.path else None; "
        f"runpy.run_path({str(REPO_ROOT / 'scripts/homologacao/agro_clean_install.py')!r}); "
        "assert importlib.util.find_spec('clean_install.catalog_validation') is not None"
    )
    # Fixed interpreter and source path; the subprocess is an import-isolation probe.
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],  # noqa: S603
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": str(Path(sys.executable).parent)},
    )
    assert completed.returncode == 0, completed.stderr
