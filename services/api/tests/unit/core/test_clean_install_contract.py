from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = API_ROOT.parent.parent
sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "homologacao"))

from clean_install import INSTALL_VERSION  # noqa: E402
from clean_install.manifest import verify_artifact_hashes  # noqa: E402
from clean_install.seed_contract import (  # noqa: E402
    SEED_CATALOGS,
    SEED_ORDER,
    SEEDS,
    apply_seeds,
    ordered_seed_rows,
    validate_seed_contract,
)


def _revision_module():
    path = API_ROOT / "migrations/clean_install/versions/20261025_clean_install_v1.py"
    spec = importlib.util.spec_from_file_location("clean_install_revision_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_seed_contract_has_explicit_order_and_only_global_required_catalogs() -> None:
    validate_seed_contract()
    assert SEED_ORDER == (
        "units",
        "product_categories",
        "operation_phases",
        "relationship_types",
        "service_types",
    )
    assert all(row.scope == "global" for row in SEEDS)
    assert len([row for row in SEEDS if row.catalog == "units"]) == 24
    unit_codes = {row.data["codigo"] for row in SEEDS if row.catalog == "units"}
    assert "d" in unit_codes
    assert "DIA" not in unit_codes
    assert len([row for row in SEEDS if row.catalog == "product_categories"]) == 30
    assert len([row for row in SEEDS if row.catalog == "operation_phases"]) == 9
    assert len([row for row in SEEDS if row.catalog == "relationship_types"]) == 11
    assert len([row for row in SEEDS if row.catalog == "service_types"]) == 10
    assert SEED_CATALOGS["commodity_conversions"]["required"] is False
    assert SEED_CATALOGS["service_types"]["required"] is True
    assert SEED_CATALOGS["zoosanitary_defaults"]["required"] is False


def test_seed_ids_and_order_are_deterministic() -> None:
    first = [(row.catalog, row.id, row.data) for row in ordered_seed_rows()]
    second = [(row.catalog, row.id, row.data) for row in ordered_seed_rows()]
    assert first == second
    assert [row.catalog for row in ordered_seed_rows()] == sorted(
        [row.catalog for row in ordered_seed_rows()], key=SEED_ORDER.index
    )


def test_seed_rows_match_current_orm_columns_and_global_scope() -> None:
    from core.database import Base
    from core.model_registry import register_models

    register_models()
    for row in SEEDS:
        table = Base.metadata.tables[row.table]
        assert set(row.data).issubset(set(table.columns.keys()))
        assert row.data.get("tenant_id") is None


class MemoryResult:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row

    def one(self):
        return self.row


class MemoryConnection:
    """Small SQLAlchemy connection substitute to exercise idempotence/drift."""

    def __init__(self):
        self.rows: dict[tuple[str, str], dict[str, object]] = {}

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        table = next((row.table for row in SEEDS if f'"{row.table}"' in sql), None)
        if table is None:
            raise AssertionError(f"Unexpected seed SQL: {sql}")
        if sql.lstrip().startswith("SELECT *"):
            seed = next(
                row
                for row in SEEDS
                if row.table == table
                and all(
                    params.get(f"key_{i}", row.data.get(column)) == row.data.get(column)
                    for i, column in enumerate(row.natural_key)
                )
            )
            key_value = "|".join(str(seed.data[column]) for column in seed.natural_key)
            return MemoryResult(self.rows.get((table, key_value)))
        if sql.lstrip().startswith("SELECT 1"):
            return MemoryResult(None)
        if sql.lstrip().startswith("INSERT"):
            row = next(row for row in SEEDS if row.table == table and row.id == params["id"])
            natural = "|".join(str(row.data[column]) for column in row.natural_key)
            values = dict(params)
            if "fases_permitidas" in values:
                import json

                values["fases_permitidas"] = json.loads(values["fases_permitidas"])
            self.rows[(table, natural)] = values
            return MemoryResult()
        raise AssertionError(f"Unexpected seed SQL: {sql}")


def test_seed_apply_is_idempotent_and_refuses_drift() -> None:
    connection = MemoryConnection()
    inserted_first = apply_seeds(connection)
    assert sum(inserted_first.values()) == len(SEEDS)
    assert sum(apply_seeds(connection).values()) == 0
    existing = next(row for row in SEEDS if row.catalog == "units")
    key = "|".join(str(existing.data[column]) for column in existing.natural_key)
    connection.rows[(existing.table, key)]["nome"] = "alterado"
    with pytest.raises(ValueError, match="Seed drift"):
        apply_seeds(connection)


def test_initial_load_catalog_subset_is_idempotent_and_excludes_optional_catalogs() -> None:
    connection = MemoryConnection()
    selected = SEED_ORDER
    first = apply_seeds(connection, catalogs=selected)
    assert first == {
        "units": 24,
        "product_categories": 30,
        "operation_phases": 9,
        "relationship_types": 11,
        "service_types": 10,
    }
    assert sum(apply_seeds(connection, catalogs=selected).values()) == 0


def test_install_revision_is_separate_and_never_stamps_historical_head(monkeypatch) -> None:
    revision = _revision_module()
    assert revision.revision == INSTALL_VERSION
    assert revision.down_revision is None
    assert revision.branch_labels == ("deepfarms_clean_install",)
    calls = []
    monkeypatch.setattr(revision, "_apply_baseline_snapshot", lambda: calls.append("baseline"))
    monkeypatch.setattr(revision, "apply_seeds", lambda bind: calls.append("seeds"))
    monkeypatch.setattr(
        revision, "validate_catalog", lambda bind, **kwargs: calls.append("validate")
    )
    monkeypatch.setattr(
        revision.op,
        "create_table",
        lambda *args, **kwargs: calls.append("manifest_table"),
    )

    class FakeBind:
        def execute(self, *_args, **_kwargs):
            calls.append("manifest_row")

    monkeypatch.setattr(revision.op, "get_bind", lambda: FakeBind())
    revision.upgrade()
    assert calls == ["baseline", "seeds", "manifest_table", "manifest_row", "validate"]
    assert "20261022_agro_admin_01b1" not in str(revision.down_revision)


def test_clean_alembic_graph_is_one_independent_snapshot_with_own_version_table() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config_path = API_ROOT / "migrations/clean_install/alembic.ini"
    config = Config(str(config_path))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [INSTALL_VERSION]
    assert script.get_bases() == [INSTALL_VERSION]
    env_source = (API_ROOT / "migrations/clean_install/env.py").read_text()
    assert 'version_table="deepfarms_install_version"' in env_source
    assert 'version_table_schema="farms"' in env_source
    assert "pg_advisory_xact_lock" in env_source


def test_install_snapshot_artifact_hashes_are_pinned() -> None:
    hashes = verify_artifact_hashes(API_ROOT)
    assert len(hashes["baseline_sha256"]) == 64
    assert len(hashes["seed_contract_sha256"]) == 64


def test_clean_runner_is_bound_to_d3f_and_exact_install_revision() -> None:
    runner_path = REPO_ROOT / "scripts/homologacao/agro_clean_install.py"
    spec = importlib.util.spec_from_file_location("agro_clean_install_test", runner_path)
    runner = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(runner)
    assert runner.INSTALL_REVISION == INSTALL_VERSION
    assert str(runner.API_ROOT) in sys.path
    with pytest.raises(Exception, match="exclusivamente ao root D3F"):
        runner._preflight(Path("other-lab"))
