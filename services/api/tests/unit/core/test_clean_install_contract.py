from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

import pytest

API_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = API_ROOT.parent.parent
sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "homologacao"))

from clean_install import INSTALL_VERSION  # noqa: E402
from clean_install.catalog_validation import (  # noqa: E402
    _constraint_inventory_differences,
    _expected_constraint_name,
    _policy_inventory_differences,
    _sequence_default_matches,
)
from clean_install.manifest import verify_artifact_hashes  # noqa: E402
from clean_install.seed_contract import (  # noqa: E402
    SEED_CATALOGS,
    SEED_ORDER,
    SEEDS,
    SeedRow,
    apply_seeds,
    ordered_seed_rows,
    validate_seed_contract,
)
from migrations.baseline_contract import (  # noqa: E402
    CHECK_CONTRACT,
    SEQUENCE_CONTRACT,
    UNIQUE_CONTRACT,
)


def _revision_module():
    path = API_ROOT / "migrations/clean_install/versions/20261025_clean_install_v1.py"
    spec = importlib.util.spec_from_file_location("clean_install_revision_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_sequence_default_accepts_search_path_dependent_regclass_rendering() -> None:
    sequence = SEQUENCE_CONTRACT["animal_genetica_id_seq"]

    assert sequence["owned_table"] == "animal_genetica"
    assert sequence["owned_column"] == "id"
    assert sequence["schema"] == "farms"
    assert sequence["default_sql"] == "nextval('farms.animal_genetica_id_seq'::regclass)"
    assert _sequence_default_matches(sequence["default_sql"], sequence, True)
    assert _sequence_default_matches(
        "nextval('animal_genetica_id_seq'::regclass)", sequence, True
    )
    assert not _sequence_default_matches(
        "nextval('animal_genetica_id_seq'::regclass)", sequence, False
    )


@pytest.mark.parametrize(
    "default",
    [
        None,
        "nextval('other.animal_genetica_id_seq'::regclass)",
        "nextval('farms.other_id_seq'::regclass)",
        "nextval('farms.animal_genetica_id_seq'::regclass) + 1",
    ],
)
def test_sequence_default_rejects_different_or_modified_expressions(default) -> None:
    sequence = SEQUENCE_CONTRACT["animal_genetica_id_seq"]

    assert not _sequence_default_matches(default, sequence, True)


def test_unnamed_unique_constraints_match_postgresql_generated_names() -> None:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    from core.database import Base
    from core.model_registry import register_models

    register_models()
    unnamed_unique = [item for item in UNIQUE_CONTRACT.values() if item["name"] is None]
    assert len(unnamed_unique) == 9

    for item in unnamed_unique:
        expected_name = f"{item['table']}_{'_'.join(item['definition'])}_key"
        ddl = str(
            CreateTable(Base.metadata.tables[item["table"]]).compile(
                dialect=postgresql.dialect()
            )
        )
        assert _expected_constraint_name(item) == expected_name
        assert len(expected_name.encode("utf-8")) < 64
        assert f"UNIQUE ({', '.join(item['definition'])})" in ddl
        assert f"CONSTRAINT {expected_name}" not in ddl

    assert all(item["name"] is not None for item in CHECK_CONTRACT.values())


def test_constraint_diagnostic_reports_missing_extra_type_and_definitions() -> None:
    expected = [
        ("farms", "tenant_data", "tenant_data_key", "UNIQUE", "UNIQUE (tenant_id, code)"),
        ("farms", "tenant_data", "ck_tenant_data", "CHECK", "CHECK (code <> '')"),
    ]
    actual = [
        ("farms", "tenant_data", "tenant_data_other_key", "UNIQUE", "UNIQUE (code)"),
        ("farms", "tenant_data", "ck_tenant_data", "UNIQUE", "UNIQUE (code)"),
    ]

    differences = _constraint_inventory_differences(expected, actual)

    assert any(
        "missing UNIQUE constraint farms.tenant_data.tenant_data_key" in item
        for item in differences
    )
    assert any(
        "unexpected UNIQUE constraint farms.tenant_data.tenant_data_other_key" in item
        for item in differences
    )
    assert any(
        "definition expected=" in item
        and "CHECK (code <> '')" in item
        and "actual='UNIQUE (code)'" in item
        for item in differences
    )
    assert any("type expected='CHECK' actual='UNIQUE'" in item for item in differences)


def test_policy_inventory_ignores_role_order_only() -> None:
    expected = [
        (
            "farms", "tenant_data", "tenant_policy", "SELECT",
            ("deepfarms_app", "deepfarms_admin"), "PERMISSIVE", "tenant_id = tenant()", None,
        )
    ]
    actual = [
        (
            "farms", "tenant_data", "tenant_policy", "SELECT",
            ["deepfarms_admin", "deepfarms_app"], "PERMISSIVE", "tenant_id = tenant()", None,
        )
    ]

    assert _policy_inventory_differences(expected, actual) == []


def test_policy_inventory_ignores_postgres_subquery_layout_whitespace() -> None:
    expected_using = (
        "((tenant_id = tenant()) OR (EXISTS ( SELECT 1 FROM tenant_passports rp "
        "WHERE (rp.id = tenant_events.passaporte_id))))"
    )
    actual_using = (
        "((tenant_id = tenant()) OR (EXISTS ( SELECT 1\n"
        "   FROM tenant_passports rp\n"
        "  WHERE (rp.id = tenant_events.passaporte_id))))"
    )
    expected = [
        (
            "farms", "tenant_events", "tenant_events_select_tenant", "SELECT",
            ("public",), "PERMISSIVE", expected_using, None,
        )
    ]
    actual = [
        (
            "farms", "tenant_events", "tenant_events_select_tenant", "SELECT",
            ["public"], "PERMISSIVE", actual_using, None,
        )
    ]

    assert _policy_inventory_differences(expected, actual) == []


def test_policy_inventory_preserves_whitespace_inside_string_literals() -> None:
    expected = [
        (
            "farms", "tenant_data", "tenant_policy", "SELECT",
            ("public",), "PERMISSIVE", "status = 'PUBLICADO'", None,
        )
    ]
    actual = [
        (
            "farms", "tenant_data", "tenant_policy", "SELECT",
            ["public"], "PERMISSIVE", "status = 'PUBLIC ADO'", None,
        )
    ]

    differences = _policy_inventory_differences(expected, actual)

    assert len(differences) == 1
    assert "USING expected=" in differences[0]


@pytest.mark.parametrize(
    ("attribute_index", "replacement", "reported_attribute"),
    [
        (3, "UPDATE", "command"),
        (4, ("deepfarms_app",), "roles"),
        (5, "RESTRICTIVE", "permissiveness"),
        (6, "tenant_id IS NOT NULL", "USING"),
        (7, "tenant_id = tenant()", "WITH CHECK"),
    ],
)
def test_policy_inventory_reports_security_relevant_differences(
    attribute_index, replacement, reported_attribute
) -> None:
    expected_row = (
        "farms", "tenant_data", "tenant_policy", "SELECT",
        ("deepfarms_app", "deepfarms_admin"), "PERMISSIVE", "tenant_id = tenant()", None,
    )
    actual_row = list(expected_row)
    actual_row[attribute_index] = replacement

    differences = _policy_inventory_differences([expected_row], [tuple(actual_row)])

    assert len(differences) == 1
    assert "farms.tenant_data.tenant_policy" in differences[0]
    assert f"{reported_attribute} expected=" in differences[0]
    assert " actual=" in differences[0]


def test_policy_inventory_reports_missing_and_unexpected_policy_identities() -> None:
    expected = [
        (
            "farms", "tenant_data", "expected_policy", "SELECT",
            ("public",), "PERMISSIVE", "true", None,
        )
    ]
    actual = [
        (
            "farms", "tenant_data", "actual_policy", "SELECT",
            ["public"], "PERMISSIVE", "true", None,
        )
    ]

    differences = _policy_inventory_differences(expected, actual)

    assert differences == [
        "missing policy farms.tenant_data.expected_policy",
        "unexpected policy farms.tenant_data.actual_policy",
    ]


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


def test_product_category_seed_orders_parent_before_child_and_grandchild() -> None:
    categories = [
        row for row in ordered_seed_rows() if row.catalog == "product_categories"
    ]
    positions = {row.id: index for index, row in enumerate(categories)}
    by_name = {row.data["nome"]: row for row in categories}

    for index, row in enumerate(categories):
        parent_id = row.data["parent_id"]
        if parent_id is not None:
            assert positions[parent_id] < index

    assert positions[by_name["Insumos Agrícolas"].id] < positions[by_name["Defensivos"].id]
    assert positions[by_name["Defensivos"].id] < positions[by_name["Herbicidas"].id]


def test_product_category_order_is_deterministic_when_seed_input_is_reversed(monkeypatch) -> None:
    import clean_install.seed_contract as contract

    expected = [
        row.id for row in ordered_seed_rows() if row.catalog == "product_categories"
    ]
    monkeypatch.setattr(contract, "SEEDS", tuple(reversed(SEEDS)))
    actual = [
        row.id for row in ordered_seed_rows() if row.catalog == "product_categories"
    ]
    assert actual == expected


def _category_row(name, row_id, parent_id) -> SeedRow:
    return SeedRow(
        "product_categories",
        "cadastros_categorias_produto",
        ("nome",),
        (("id", str(row_id)), ("nome", name), ("parent_id", parent_id)),
    )


def test_product_category_order_rejects_missing_parent(monkeypatch) -> None:
    import clean_install.seed_contract as contract

    missing_parent = uuid4()
    child = _category_row("Filha", uuid4(), missing_parent)
    monkeypatch.setattr(contract, "SEEDS", (child,))
    with pytest.raises(ValueError, match="missing parent"):
        ordered_seed_rows()


def test_product_category_order_rejects_cycles(monkeypatch) -> None:
    import clean_install.seed_contract as contract

    parent_id = uuid4()
    child_id = uuid4()
    rows = (
        _category_row("Pai", parent_id, child_id),
        _category_row("Filha", child_id, parent_id),
    )
    monkeypatch.setattr(contract, "SEEDS", rows)
    with pytest.raises(ValueError, match="cycle"):
        ordered_seed_rows()


def test_product_category_contract_has_no_cycles() -> None:
    categories = [row for row in ordered_seed_rows() if row.catalog == "product_categories"]
    assert len(categories) == len([row for row in SEEDS if row.catalog == "product_categories"])


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
            if table == "cadastros_categorias_produto" and params["parent_id"] is not None:
                parent_exists = any(
                    existing_table == table and existing.get("id") == params["parent_id"]
                    for (existing_table, _), existing in self.rows.items()
                )
                if not parent_exists:
                    raise AssertionError("Category parent must be inserted before its child")
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


def test_seed_preserves_existing_product_category_id() -> None:
    connection = MemoryConnection()
    category = next(
        row
        for row in SEEDS
        if row.catalog == "product_categories" and row.data["nome"] == "Adjuvantes"
    )
    natural_key = "|".join(str(category.data[column]) for column in category.natural_key)
    existing_id = uuid4()
    connection.rows[(category.table, natural_key)] = category.data | {"id": existing_id}

    inserted = apply_seeds(connection, catalogs=("product_categories",))

    assert inserted["product_categories"] == 29
    assert connection.rows[(category.table, natural_key)]["id"] == existing_id


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
