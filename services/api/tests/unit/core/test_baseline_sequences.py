from __future__ import annotations

from importlib import import_module
from pathlib import Path

from sqlalchemy import BigInteger, Integer
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from core.database import Base
from core.model_registry import baseline_candidate_tables, register_models
from migrations.baseline_contract import (
    EXCLUDED_SEQUENCE_NAMES,
    REQUIRED_SEQUENCE_NAMES,
    SEQUENCE_CONTRACT,
    SEQUENCE_NAMES,
)


def _orm_autoincrement_columns() -> dict[str, tuple[str, str]]:
    register_models()
    result = {}
    for table_name in baseline_candidate_tables():
        table = Base.metadata.tables[table_name]
        column = table.autoincrement_column
        if column is None or not isinstance(column.type, Integer):
            continue
        result[f"{table_name}_{column.name}_seq"] = (
            table_name,
            column.name,
        )
    return result


def test_sequence_contract_is_derived_from_orm_serial_columns() -> None:
    expected = _orm_autoincrement_columns()
    assert len(expected) == 33
    assert set(SEQUENCE_CONTRACT) == REQUIRED_SEQUENCE_NAMES == set(expected)

    for sequence_name, (table_name, column_name) in expected.items():
        column = Base.metadata.tables[table_name].c[column_name]
        contract = SEQUENCE_CONTRACT[sequence_name]
        assert contract["schema"] == "farms"
        assert contract["owned_table"] == table_name
        assert contract["owned_column"] == column_name
        assert contract["ownership"] == "OWNED_BY_COLUMN"
        assert contract["creation_authority"] == "ORM_TABLE_DDL"
        assert contract["generation"] == (
            "BIGSERIAL" if isinstance(column.type, BigInteger) else "SERIAL"
        )
        assert contract["default_sql"] == (
            f"nextval('farms.{sequence_name}'::regclass)"
        )


def test_serial_and_bigserial_ddl_remains_the_orm_authority() -> None:
    register_models()
    for sequence_name, contract in SEQUENCE_CONTRACT.items():
        table = Base.metadata.tables[str(contract["owned_table"])]
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert "SERIAL" in ddl
        if contract["generation"] == "BIGSERIAL":
            assert "BIGSERIAL" in ddl
        else:
            assert "BIGSERIAL" not in ddl
        assert sequence_name == f"{table.name}_{contract['owned_column']}_seq"


def test_baseline_has_no_explicit_sequence_ddl_or_suffix_workaround() -> None:
    revision = import_module("migrations.versions.20260908_baseline_deepfarms_v1")
    source = Path(revision.__file__).read_text(encoding="utf-8")
    assert "def _create_sequences" not in source
    assert "CREATE SEQUENCE" not in source
    assert "_create_sequences()" not in source
    assert "DROP SEQUENCE IF EXISTS farms." in source
    assert all(not name.endswith("seq1") for name in SEQUENCE_CONTRACT)


def test_historical_sequence_reference_is_not_mistaken_for_clean_install_ddl() -> None:
    assert len(SEQUENCE_NAMES) == 35
    assert len(EXCLUDED_SEQUENCE_NAMES) == 3
    assert "amostras_id_seq" in EXCLUDED_SEQUENCE_NAMES
    assert "mapas_fertilidade_id_seq" in EXCLUDED_SEQUENCE_NAMES
    assert "territory_legacy_backup_01h2_id_seq" in EXCLUDED_SEQUENCE_NAMES
    assert not (EXCLUDED_SEQUENCE_NAMES & REQUIRED_SEQUENCE_NAMES)


def test_sankhya_sync_logs_bigserial_is_part_of_clean_install_contract() -> None:
    sequence_name = "sankhya_sync_logs_id_seq"
    contract = SEQUENCE_CONTRACT[sequence_name]
    assert contract["owned_table"] == "sankhya_sync_logs"
    assert contract["owned_column"] == "id"
    assert contract["data_type"] == "bigint"
    assert contract["generation"] == "BIGSERIAL"
