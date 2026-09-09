"""Regression tests for the read-only baseline metadata audit."""

import re
from collections import Counter

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from core.database import Base
from core.model_registry import baseline_candidate_tables, register_models
from migrations.metadata_audit import audit_baseline_metadata


def test_audit_counts_all_baseline_foreign_keys() -> None:
    """Ensure the audit covers the complete approved ORM scope."""
    result = audit_baseline_metadata()
    assert result["baseline_tables"] == 344
    assert result["foreign_keys"] == 892


def test_audit_closes_type_blockers() -> None:
    """Require every baseline FK to use compatible PostgreSQL types."""
    result = audit_baseline_metadata()
    assert result["type_or_key_issues"] == ()


def test_audit_closes_composite_parent_key_blockers() -> None:
    """Require every composite FK to have a compatible parent key."""
    result = audit_baseline_metadata()
    assert result["composite_without_key"] == ()


def test_audit_has_no_scope_or_check_reference_leaks() -> None:
    """Ensure excluded tables and missing CHECK columns are reported as zero."""
    result = audit_baseline_metadata()
    assert result["outside_baseline"] == ()
    assert result["invalid_checks"] == ()


def test_audit_closes_tenant_integrity_contract() -> None:
    """Require all seven historical Tenant Integrity relations."""
    result = audit_baseline_metadata()
    assert result["missing_tenant_composite"] == ()


def test_tenant_integrity_constraints_are_explicit() -> None:
    """Require the closed composite FK and UNIQUE names in ORM metadata."""
    register_models()
    expected_unique = {
        "uq_unidades_produtivas_tenant_id_id",
        "uq_cadastros_equipamentos_tenant_id",
        "uq_frota_jornadas_tenant_id",
        "uq_estoque_depositos_tenant_id",
    }
    actual_unique = {
        constraint.name
        for table in Base.metadata.tables.values()
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert expected_unique <= actual_unique
    expected_fks = {
        "fk_cp_tenant_deposito",
        "fk_fa_tenant_equipamento",
        "fk_fau_tenant_jornada",
    }
    actual_fks = {
        constraint.name
        for table in Base.metadata.tables.values()
        for constraint in table.foreign_key_constraints
    }
    assert expected_fks <= actual_fks


def test_index_audit_has_no_namespace_or_definition_collisions() -> None:
    """Require the baseline index inventory to be executable once per name."""
    result = audit_baseline_metadata()
    assert result["total_indexes"] == 1029
    assert result["duplicate_index_names"] == {}
    assert result["duplicate_index_definitions"] == {}
    assert result["index_relation_name_collisions"] == ()
    assert result["indexes_missing_columns"] == ()
    assert result["redundant_unique_indexes"] == ()


def test_index_audit_covers_campo_type_once() -> None:
    """Prevent regression of the historical ix_campo_tarefas_type collision."""
    register_models()
    indexes = [
        index
        for name in baseline_candidate_tables()
        for index in Base.metadata.tables[name].indexes
        if index.name == "ix_campo_tarefas_type"
    ]
    assert len(indexes) == 1


def test_compiled_baseline_indexes_emit_each_relation_name_once() -> None:
    """Prevent duplicate CREATE INDEX relation names in generated DDL."""
    register_models()
    statements = [
        str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        for name in baseline_candidate_tables()
        for index in Base.metadata.tables[name].indexes
    ]
    names = [
        match.group(1).strip('"')
        for statement in statements
        if (match := re.search(r"CREATE (?:UNIQUE )?INDEX\s+([^\s(]+)", statement))
    ]
    assert len(names) == len(statements)
    assert {name: count for name, count in Counter(names).items() if count > 1} == {}
