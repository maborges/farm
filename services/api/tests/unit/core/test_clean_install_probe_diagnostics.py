"""Unit tests for the clean-install probe validator, physical index resolution, and installer contract."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, call

import pytest
from sqlalchemy.dialects import postgresql

from clean_install import INSTALL_VERSION
from clean_install.catalog_validation import (
    _constraint_inventory_differences,
    _probe_canonical_check_definitions,
    _resolve_expected_indexes,
)
from clean_install.installer_contract import (
    ALL_EXCLUDED_TABLES,
    HISTORICAL_EXCLUDED_TABLES,
    INSTALLER_SCHEMA,
    INSTALLER_TABLES,
    MANIFEST_CHECK_NAME,
    MANIFEST_COLUMNS,
    MANIFEST_TABLE,
    VERSION_TABLE,
    get_installer_check_contract,
    validate_installer_objects,
    validate_manifest_columns,
    validate_manifest_constraints,
    validate_manifest_row,
    validate_version_row,
)
from clean_install.manifest import (
    BASELINE_REVISION,
    BASELINE_SHA256,
    INSTALL_VERSION as MANIFEST_INSTALL_VERSION,
    SEED_CONTRACT_SHA256,
    SEED_CONTRACT_VERSION,
)
from core.database import Base
from core.model_registry import register_models
from migrations.baseline_contract import CHECK_CONTRACT, INDEX_CONTRACT, UNIQUE_CONTRACT


def test_manifest_reexports_install_version() -> None:
    """Verify clean_install.manifest exports INSTALL_VERSION for backward compatibility."""
    assert MANIFEST_INSTALL_VERSION == INSTALL_VERSION
    assert MANIFEST_INSTALL_VERSION == "deepfarms_clean_install_v1"


def test_installer_contract_constants_and_tables() -> None:
    """Verify installer contract table definitions and exclusions."""
    assert INSTALLER_SCHEMA == "farms"
    assert MANIFEST_TABLE == "deepfarms_install_manifest"
    assert VERSION_TABLE == "deepfarms_install_version"
    assert "alembic_version" in HISTORICAL_EXCLUDED_TABLES
    assert set(INSTALLER_TABLES).issubset(set(ALL_EXCLUDED_TABLES))
    assert MANIFEST_CHECK_NAME == "ck_deepfarms_install_manifest_singleton"

    checks = get_installer_check_contract()
    assert len(checks) == 1
    assert checks[0] == (
        "farms",
        "deepfarms_install_manifest",
        "ck_deepfarms_install_manifest_singleton",
        "CHECK",
        "singleton IS TRUE",
    )


def test_resolve_expected_indexes_truncates_long_names_reproducing_postgresql() -> None:
    """Verify that all indexes exceeding 63 bytes are truncated matching PostgreSQL behavior."""
    register_models()
    mock_connection = MagicMock()
    mock_connection.dialect = postgresql.dialect()

    resolved = _resolve_expected_indexes(
        mock_connection,
        INDEX_CONTRACT,
        Base.metadata.tables,
    )
    assert len(resolved) == len(INDEX_CONTRACT)
    assert all(len(name) <= 63 for _, name in resolved)

    # Verify the 5 long index names specifically
    long_items = {
        item["name"]: item["table"]
        for item in INDEX_CONTRACT.values()
        if len(item["name"]) > 63
    }
    assert len(long_items) == 5

    resolved_map = dict(resolved)
    for long_name, table in long_items.items():
        # Physical name should be in resolved and must be <= 63 chars with 4-char hash suffix
        physical_name = [name for t, name in resolved if t == table and name != long_name]
        assert len(physical_name) >= 1
        assert any(len(n) == 60 for n in physical_name)


def test_probe_canonical_check_definitions_skips_non_postgresql() -> None:
    """Verify probe returns empty dict when dialect is not PostgreSQL."""
    mock_connection = MagicMock()
    mock_connection.dialect.name = "sqlite"

    checks_by_table = {"culturas": [{"name": "ck_test", "definition": "ciclo_dias > 0"}]}
    result = _probe_canonical_check_definitions(mock_connection, checks_by_table)
    assert result == {}


def test_probe_canonical_check_definitions_executes_lifecycle_and_extracts_definitions() -> None:
    """Verify probe lifecycle: temp table creation, alter constraint, query def, drop."""
    mock_connection = MagicMock()
    mock_connection.dialect.name = "postgresql"

    # Simulate query result for probe table pg_get_constraintdef
    mock_connection.execute.return_value.all.return_value = [
        ("ck_culturas_ciclo_dias_pos", "CHECK ((ciclo_dias > 0))")
    ]

    checks_by_table = {
        "culturas": [
            {"name": "ck_culturas_ciclo_dias_pos", "definition": "ciclo_dias > 0"}
        ]
    }
    probe_defs = _probe_canonical_check_definitions(mock_connection, checks_by_table)

    assert ("culturas", "ck_culturas_ciclo_dias_pos") in probe_defs
    assert probe_defs[("culturas", "ck_culturas_ciclo_dias_pos")] == "CHECK ((ciclo_dias > 0))"

    executed_sqls = [str(call_args[0][0]) for call_args in mock_connection.execute.call_args_list]
    assert any("CREATE TEMP TABLE \"_df_probe_culturas\"" in sql for sql in executed_sqls)
    assert any("ALTER TABLE \"_df_probe_culturas\" ADD CONSTRAINT" in sql for sql in executed_sqls)
    assert any("pg_my_temp_schema()" in sql for sql in executed_sqls)
    assert any("DROP TABLE IF EXISTS \"_df_probe_culturas\"" in sql for sql in executed_sqls)


def test_constraint_inventory_detects_tampered_check_definition() -> None:
    """Negative test: tampered CHECK expression triggers precise diagnostic diff."""
    expected = [
        ("farms", "culturas", "ck_culturas_ciclo_dias_pos", "CHECK", "CHECK ((ciclo_dias > 0))")
    ]
    actual_tampered = [
        ("farms", "culturas", "ck_culturas_ciclo_dias_pos", "CHECK", "CHECK ((ciclo_dias >= 0))")
    ]

    diffs = _constraint_inventory_differences(expected, actual_tampered)
    assert len(diffs) == 1
    assert "farms.culturas.ck_culturas_ciclo_dias_pos: definition expected='CHECK ((ciclo_dias > 0))' actual='CHECK ((ciclo_dias >= 0))'" in diffs[0]


def test_constraint_inventory_detects_unexpected_and_missing_checks() -> None:
    """Negative test: missing and unexpected constraints are clearly differentiated."""
    expected = [
        ("farms", "culturas", "ck_expected", "CHECK", "CHECK ((ciclo_dias > 0))")
    ]
    actual = [
        ("farms", "culturas", "ck_unexpected", "CHECK", "CHECK ((ciclo_dias > 0))")
    ]

    diffs = _constraint_inventory_differences(expected, actual)
    assert any("missing CHECK constraint farms.culturas.ck_expected" in d for d in diffs)
    assert any("unexpected CHECK constraint farms.culturas.ck_unexpected" in d for d in diffs)


def test_validate_manifest_columns_positive_and_negative() -> None:
    """Verify manifest column validation passes when columns match and fails on tampering."""
    mock_conn = MagicMock()
    # Positive case: exact matching columns and non-nullable
    mock_conn.execute.return_value.all.return_value = [
        (col, False) for col in MANIFEST_COLUMNS.keys()
    ]
    assert validate_manifest_columns(mock_conn) == []

    # Negative case: missing column and wrong nullability
    mock_conn.execute.return_value.all.return_value = [
        ("singleton", True),  # should be False
        # install_version is missing
        ("baseline_revision", False),
        ("baseline_sha256", False),
        ("seed_contract_version", False),
        ("seed_contract_sha256", False),
        ("installed_at", False),
        ("extra_column", False),  # unexpected
    ]
    errors = validate_manifest_columns(mock_conn)
    assert any("missing columns: ['install_version']" in e for e in errors)
    assert any("unexpected columns: ['extra_column']" in e for e in errors)
    assert any("singleton nullability expected=False actual=True" in e for e in errors)


def test_validate_manifest_constraints_positive_and_negative() -> None:
    """Verify manifest constraint validation detects missing or tampered singleton CHECK."""
    mock_conn = MagicMock()
    # Positive case: CHECK singleton IS TRUE + PK
    mock_conn.execute.return_value.all.return_value = [
        ("ck_deepfarms_install_manifest_singleton", "c", "CHECK ((singleton IS TRUE))"),
        ("deepfarms_install_manifest_pkey", "p", "PRIMARY KEY (singleton)"),
    ]
    assert validate_manifest_constraints(mock_conn) == []

    # Negative case: missing CHECK and missing PK
    mock_conn.execute.return_value.all.return_value = []
    errors = validate_manifest_constraints(mock_conn)
    assert any("missing CHECK constraint ck_deepfarms_install_manifest_singleton" in e for e in errors)
    assert any("missing PRIMARY KEY constraint" in e for e in errors)


def test_validate_manifest_row_positive_and_negative() -> None:
    """Verify manifest row validation detects modified artifact hashes or versions."""
    mock_conn = MagicMock()
    hashes = {
        "baseline_sha256": BASELINE_SHA256,
        "seed_contract_sha256": SEED_CONTRACT_SHA256,
    }
    # Positive case
    mock_conn.execute.return_value.one_or_none.return_value = (
        True,
        INSTALL_VERSION,
        BASELINE_REVISION,
        BASELINE_SHA256,
        SEED_CONTRACT_VERSION,
        SEED_CONTRACT_SHA256,
    )
    assert validate_manifest_row(mock_conn, hashes) == []

    # Negative case: hash mismatch
    mock_conn.execute.return_value.one_or_none.return_value = (
        True,
        INSTALL_VERSION,
        BASELINE_REVISION,
        "tampered_baseline_hash_ffffffffffffffffffffffffffffffffffffffff",
        SEED_CONTRACT_VERSION,
        SEED_CONTRACT_SHA256,
    )
    errors = validate_manifest_row(mock_conn, hashes)
    assert len(errors) == 1
    assert "values mismatch" in errors[0]


def test_validate_version_row_positive_and_negative() -> None:
    """Verify deepfarms_install_version row validation."""
    mock_conn = MagicMock()
    # Positive case
    mock_conn.execute.return_value.scalar_one_or_none.return_value = INSTALL_VERSION
    assert validate_version_row(mock_conn) == []

    # Negative case: wrong version
    mock_conn.execute.return_value.scalar_one_or_none.return_value = "wrong_version_v0"
    errors = validate_version_row(mock_conn)
    assert len(errors) == 1
    assert "version expected='deepfarms_clean_install_v1' actual='wrong_version_v0'" in errors[0]

    # Negative case: missing row
    mock_conn.execute.return_value.scalar_one_or_none.return_value = None
    assert validate_version_row(mock_conn) == ["farms.deepfarms_install_version row is missing"]


def test_validate_installer_objects_detects_missing_table() -> None:
    """Verify validate_installer_objects fails when manifest table is absent."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.scalar_one.return_value = False
    errors = validate_installer_objects(mock_conn)
    assert errors == ["farms.deepfarms_install_manifest table does not exist"]

