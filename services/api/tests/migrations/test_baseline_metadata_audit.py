"""Regression tests for the read-only baseline metadata audit."""

from core.database import Base
from core.model_registry import register_models
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
