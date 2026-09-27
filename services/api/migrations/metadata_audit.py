"""Read-only structural audit for the DeepFarms baseline metadata."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex
from sqlalchemy.sql.sqltypes import String

from core.database import Base
from core.model_registry import baseline_candidate_tables, register_models
from migrations.baseline_contract import SEQUENCE_NAMES

TENANT_COMPOSITE_CONTRACT = frozenset(
    {
        ("cadastros_areas_rurais", "fk_car_tenant_unidade_produtiva"),
        ("estoque_depositos", "fk_ed_tenant_unidade_produtiva"),
        ("cadastros_equipamentos", "fk_ce_tenant_unidade_produtiva"),
        ("frota_jornadas_equipamento", "fk_fje_tenant_unidade_produtiva"),
        ("frota_apontamentos_uso", "fk_fau_tenant_jornada"),
        ("frota_abastecimentos", "fk_fa_tenant_equipamento"),
    }
)


@dataclass(frozen=True)
class ForeignKeyIssue:
    """Describe one FK defect that can prevent PostgreSQL DDL."""

    source_table: str
    constraint: str | None
    source_columns: tuple[str, ...]
    source_types: tuple[str, ...]
    target_table: str
    target_columns: tuple[str, ...]
    target_types: tuple[str, ...]
    problem: str


def _type_name(column: object) -> str:
    """Return a compact SQLAlchemy type label for audit output."""
    type_ = column.type
    length = getattr(type_, "length", None)
    return f"{type_.__class__.__name__}({length})" if length else type_.__class__.__name__


def _candidate_keys(table: object) -> set[tuple[str, ...]]:
    """Return PK, UNIQUE constraint and non-expression UNIQUE index shapes."""
    keys = {tuple(column.name for column in table.primary_key.columns)}
    keys.update(
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    )
    keys.update(
        tuple(column.name for column in index.columns)
        for index in table.indexes
        if index.unique and not index.expressions
    )
    return keys


def _types_compatible(source: object, target: object) -> bool:
    """Apply PostgreSQL-safe affinity checks, allowing varchar length variance."""
    source_sql = str(source.type.compile(dialect=postgresql.dialect())).upper()
    target_sql = str(target.type.compile(dialect=postgresql.dialect())).upper()
    if source_sql == "UUID" or target_sql == "UUID":
        return source_sql == target_sql
    if source.type._compare_type_affinity(target.type) is False:
        return False
    if isinstance(source.type, String) and isinstance(target.type, String):
        return True
    return source.type.__class__ is target.type.__class__


def _check_references(table: object, constraint: object) -> tuple[str, ...]:
    """Find textual CHECK identifiers absent from the table columns."""
    keywords = {
        "AND", "OR", "NOT", "NULL", "IS", "TRUE", "FALSE", "IN", "LIKE",
        "BETWEEN", "CASE", "WHEN", "THEN", "ELSE", "END", "AS", "COALESCE",
        "BTRIM", "LENGTH", "LOWER", "UPPER", "EXTRACT", "NOW", "CURRENT_DATE",
        "CURRENT_TIMESTAMP", "INTERVAL", "DATE", "NUMERIC", "VARCHAR", "NEW", "OLD",
    }
    expression = re.sub(r"'(?:''|[^'])*'", "", str(constraint.sqltext))
    identifiers = set(re.findall(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)", expression))
    return tuple(
        sorted(name for name in identifiers if name.upper() not in keywords and name not in table.c)
    )


def _index_definition(index: Index) -> tuple[object, ...]:
    """Return the schema-relevant identity of an index."""
    where = str(index.dialect_options["postgresql"].get("where", ""))
    return (index.table.name, tuple(str(item) for item in index.expressions), index.unique, where)


def _audit_indexes(baseline: set[str]) -> dict[str, object]:
    """Audit all baseline indexes in the global PostgreSQL namespace."""
    indexes = [index for name in baseline for index in Base.metadata.tables[name].indexes]
    by_name: defaultdict[str, list[Index]] = defaultdict(list)
    by_definition: defaultdict[tuple[object, ...], list[Index]] = defaultdict(list)
    missing_columns: list[tuple[str, str | None, str]] = []
    unique_redundancies: list[tuple[str, str | None, tuple[str, ...]]] = []
    relation_names = baseline | set(SEQUENCE_NAMES)

    for index in indexes:
        by_name[index.name].append(index)
        by_definition[_index_definition(index)].append(index)
        try:
            CreateIndex(index).compile(dialect=postgresql.dialect())
        except Exception as error:  # pragma: no cover - defensive metadata guard
            missing_columns.append((index.table.name, index.name, str(error)))
        names = tuple(column.name for column in index.columns)
        if any(name not in index.table.c for name in names):
            missing_columns.append((index.table.name, index.name, ",".join(names)))
        if index.unique and names in {
            tuple(column.name for column in constraint.columns)
            for constraint in index.table.constraints
            if isinstance(constraint, UniqueConstraint)
        }:
            unique_redundancies.append((index.table.name, index.name, names))
    duplicate_names = {
        name: tuple(
            (index.table.name, tuple(column.name for column in index.columns))
            for index in values
        )
        for name, values in by_name.items()
        if len(values) > 1
    }
    duplicate_definitions = {
        definition: tuple(index.name for index in values)
        for definition, values in by_definition.items()
        if len(values) > 1
    }
    relation_collisions = tuple(sorted(name for name in by_name if name in relation_names))
    return {
        "total_indexes": len(indexes),
        "duplicate_index_names": duplicate_names,
        "duplicate_index_definitions": duplicate_definitions,
        "index_relation_name_collisions": relation_collisions,
        "indexes_missing_columns": tuple(missing_columns),
        "redundant_unique_indexes": tuple(unique_redundancies),
    }


def audit_baseline_metadata() -> dict[str, object]:
    """Audit FKs, candidate keys, CHECK references and baseline scope read-only."""
    register_models()
    baseline = baseline_candidate_tables()
    issues: list[ForeignKeyIssue] = []
    composite_without_key: list[ForeignKeyIssue] = []
    outside: list[tuple[str, str | None, str]] = []
    invalid_checks: list[tuple[str, str | None, tuple[str, ...]]] = []
    foreign_keys = [
        fk for name in baseline for fk in Base.metadata.tables[name].foreign_key_constraints
    ]
    present_tenant_composite = {
        (fk.table.name, fk.name)
        for fk in foreign_keys
        if len(fk.elements) > 1 and fk.name
    }

    for source_name in sorted(baseline):
        table = Base.metadata.tables[source_name]
        for check in table.constraints:
            if check.__class__.__name__ == "CheckConstraint":
                missing = _check_references(table, check)
                if missing:
                    invalid_checks.append((source_name, check.name, missing))
        for fk in table.foreign_key_constraints:
            source = tuple(element.parent for element in fk.elements)
            target = tuple(element.column for element in fk.elements)
            target_table = fk.referred_table
            issue = ForeignKeyIssue(
                source_name, fk.name, tuple(column.name for column in source),
                tuple(_type_name(column) for column in source),
                target_table.name,
                tuple(column.name for column in target),
                tuple(_type_name(column) for column in target),
                "",
            )
            if target_table.name not in baseline:
                outside.append((source_name, fk.name, target_table.name))
                continue
            if any(
                not _types_compatible(left, right)
                for left, right in zip(source, target, strict=True)
            ):
                issues.append(issue.__class__(
                    **{**issue.__dict__, "problem": "tipos PostgreSQL incompatíveis"}
                ))
            if tuple(column.name for column in source) != tuple(column.name for column in target):
                target_names = tuple(column.name for column in target)
                if len(source) > 1 and target_names not in _candidate_keys(target_table):
                    composite_without_key.append(
                        issue.__class__(
                            **{**issue.__dict__, "problem": "pai sem PK/UNIQUE compatível"}
                        )
                    )
                elif len(source) == 1 and target_names not in _candidate_keys(target_table):
                    issues.append(
                        issue.__class__(
                            **{**issue.__dict__, "problem": "pai sem PK/UNIQUE compatível"}
                        )
                    )

    result = {
        "baseline_tables": len(baseline),
        "foreign_keys": len(foreign_keys),
        "type_or_key_issues": tuple(issues),
        "composite_without_key": tuple(composite_without_key),
        "outside_baseline": tuple(outside),
        "invalid_checks": tuple(invalid_checks),
        "missing_tenant_composite": tuple(
            sorted(TENANT_COMPOSITE_CONTRACT - present_tenant_composite)
        ),
        "unnamed_foreign_keys": sum(fk.name is None for fk in foreign_keys),
    }
    result.update(_audit_indexes(baseline))
    return result
