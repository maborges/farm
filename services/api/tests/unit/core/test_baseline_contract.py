from core.database import Base
from core.model_registry import baseline_candidate_tables, register_models
from migrations.baseline_contract import (
    BASELINE_ORM_TABLE_COUNT,
    BASELINE_SCHEMA,
    CHECK_CONTRACT,
    CONTRACT_STATUS,
    DISCOVERED_MODEL_COUNT,
    ENUM_CONTRACT,
    FK_CONTRACT,
    FK_DECISIONS,
    FUNCTION_CONTRACT,
    INDEX_CONTRACT,
    NULLABLE_DECISIONS,
    PHYSICAL_TABLES_OUTSIDE_BASELINE,
    POLICY_CONTRACT,
    POLICY_INVALID_COUNT,
    POLICY_OUTSIDE_BASELINE_COUNT,
    POSTGRESQL_VALIDATION_PENDING,
    REFERENCE_COMPARISON,
    REQUIRED_SEQUENCE_NAMES,
    RLS_CONTRACT,
    RLS_ENABLED_TABLES,
    RLS_FORCED_TABLES,
    SEQUENCE_CONTRACT,
    SEQUENCE_NAMES,
    SERVER_DEFAULT_DECISIONS,
    TRIGGER_CONTRACT,
    TYPE_DECISIONS,
    UNIQUE_CONTRACT,
    UNRESOLVED_COUNTS,
)


def test_baseline_revision_is_independent_and_uses_contract_sources() -> None:
    from importlib import import_module
    from pathlib import Path

    revision = import_module(
        "migrations.versions.20260908_baseline_deepfarms_v1"
    )
    assert revision.revision == "baseline_deepfarms_v1"
    assert revision.down_revision is None
    assert len(revision.baseline_candidate_tables()) == BASELINE_ORM_TABLE_COUNT == 348
    assert "MetaData.create_all(" not in revision.__doc__
    source = Path(revision.__file__).read_text()
    assert "Base.metadata.create_all(" not in source
    assert "Base.metadata.drop_all(" not in source


def test_contract_scope_and_schema_are_deterministic() -> None:
    register_models()
    assert BASELINE_SCHEMA == "farms"
    assert len(Base.metadata.tables) == DISCOVERED_MODEL_COUNT
    assert len(baseline_candidate_tables()) == BASELINE_ORM_TABLE_COUNT
    assert len(NULLABLE_DECISIONS) == 10
    assert len(FK_DECISIONS) == 1


def test_contract_has_no_invalid_animal_genetica_target() -> None:
    register_models()
    assert all(
        not fk.target_fullname.startswith("lotes.")
        for table in Base.metadata.tables.values()
        for fk in table.foreign_keys
    )
    assert FK_DECISIONS[("animal_genetica", "animal_id")]["decision"] == "NO_FOREIGN_KEY"


def test_all_baseline_foreign_keys_have_explicit_valid_contract() -> None:
    assert len(FK_CONTRACT) > 0
    assert all(item["classification"] != "INVALID" for item in FK_CONTRACT.values())
    assert all(
        item["classification"] not in {"UNKNOWN", "PENDING", "UNRESOLVED"}
        for item in FK_CONTRACT.values()
    )
    assert all(item["target_table"] and item["target_columns"] for item in FK_CONTRACT.values())
    assert all(
        not (
            item["target_table"] == "tenants"
            and item["baseline_on_delete"] == "CASCADE"
        )
        for item in FK_CONTRACT.values()
    )


def test_non_orm_inventory_is_explicit_and_read_only() -> None:
    assert len(ENUM_CONTRACT) == 34
    assert sum(len(values) for values in ENUM_CONTRACT.values()) == 146
    assert len(SEQUENCE_NAMES) == 35
    assert len(RLS_ENABLED_TABLES) == 49
    assert len(RLS_FORCED_TABLES) == 48
    assert all(item["decision"] == "INCLUDE" for item in FUNCTION_CONTRACT.values())
    assert all(item["decision"] == "INCLUDE" for item in TRIGGER_CONTRACT.values())
    assert "balanca_pesagens" in PHYSICAL_TABLES_OUTSIDE_BASELINE
    assert CONTRACT_STATUS == "NO-GO"


def test_structural_closure_gate_cannot_hide_open_decisions() -> None:
    assert UNRESOLVED_COUNTS["fk_target"] == 0
    assert UNRESOLVED_COUNTS["nullable"] == 0
    assert UNRESOLVED_COUNTS["function"] == 0
    assert UNRESOLVED_COUNTS["trigger"] == 0
    assert UNRESOLVED_COUNTS["required_index"] == 0
    assert UNRESOLVED_COUNTS["unique"] > 0
    assert UNRESOLVED_COUNTS["check"] > 0
    assert REFERENCE_COMPARISON["aligned_with_current_head"] is False
    assert POSTGRESQL_VALIDATION_PENDING
    assert len(UNIQUE_CONTRACT) == 76
    assert len(CHECK_CONTRACT) == 76
    assert len(INDEX_CONTRACT) == 1063
    assert all(item["source"] == "ORM_CURRENT" for item in UNIQUE_CONTRACT.values())
    assert all(item["source"] == "ORM_CURRENT" for item in CHECK_CONTRACT.values())
    assert all(item["source"] == "ORM_CURRENT" for item in INDEX_CONTRACT.values())
    assert all(
        item["historical_reference_parity"] == "NOT_PROVEN"
        for item in (*UNIQUE_CONTRACT.values(), *CHECK_CONTRACT.values())
    )
    assert any(value > 0 for key, value in UNRESOLVED_COUNTS.items() if key != "fk_target")
    assert CONTRACT_STATUS != "GO"


def test_rls_and_policies_are_complete_for_the_baseline() -> None:
    baseline = baseline_candidate_tables()
    assert len(RLS_CONTRACT) == len(baseline) == BASELINE_ORM_TABLE_COUNT == 348
    assert all(
        item["classification"]
        in {"RLS_REQUIRED", "RLS_REQUIRED_NO_FORCE", "RLS_NOT_REQUIRED"}
        for item in RLS_CONTRACT.values()
    )
    assert len(POLICY_CONTRACT) == 188
    assert POLICY_INVALID_COUNT == 0
    assert POLICY_OUTSIDE_BASELINE_COUNT == 0
    assert all(item["table"] in baseline for item in POLICY_CONTRACT.values())
    assert all(item["command"] and item["roles"] for item in POLICY_CONTRACT.values())
    assert RLS_CONTRACT["propriedade_imovel"]["enabled"] is True
    assert RLS_CONTRACT["propriedade_imovel"]["forced"] is False


def test_minimum_type_default_and_sequence_contract_is_executable() -> None:
    assert TYPE_DECISIONS["type_blocker_for_create"] == 0
    assert SERVER_DEFAULT_DECISIONS["unresolved_required_server_default"] == 0
    assert len(SEQUENCE_CONTRACT) == 33
    assert len(REQUIRED_SEQUENCE_NAMES) == 33
    assert set(SEQUENCE_CONTRACT) == REQUIRED_SEQUENCE_NAMES
    assert all(item["creation_authority"] == "ORM_TABLE_DDL" for item in SEQUENCE_CONTRACT.values())

    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    register_models()
    for name in baseline_candidate_tables():
        str(CreateTable(Base.metadata.tables[name]).compile(dialect=postgresql.dialect()))
