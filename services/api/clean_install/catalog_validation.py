"""Runtime catalog gate for the clean-install snapshot; never mutates schema."""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.engine import Connection

_POLICY_ATTRIBUTE_NAMES = (
    "command",
    "roles",
    "permissiveness",
    "USING",
    "WITH CHECK",
)
_DOLLAR_QUOTE = re.compile(r"\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$")


def _normalize_policy_expression(expression: str | None) -> str | None:
    """Collapse SQL whitespace outside quoted values and identifiers.

    Args:
        expression: Deparsed PostgreSQL policy expression.

    Returns:
        The expression with insignificant whitespace runs collapsed.

    Raises:
        None.
    """
    if expression is None:
        return None
    normalized = []
    pending_space = False
    index = 0
    while index < len(expression):
        char = expression[index]
        if char.isspace():
            pending_space = True
            index += 1
            continue
        if pending_space and normalized:
            normalized.append(" ")
        pending_space = False
        if expression.startswith(("--", "/*"), index):
            index = _copy_sql_comment(expression, index, normalized)
            continue
        if char in "'\"":
            index = _copy_quoted_sql_token(expression, index, normalized)
            continue
        if char == "$":
            delimiter = _DOLLAR_QUOTE.match(expression, index)
            if delimiter:
                index = _copy_dollar_quoted_token(
                    expression, index, delimiter.group(), normalized
                )
                continue
        normalized.append(char)
        index += 1
    return "".join(normalized).strip()


def _copy_quoted_sql_token(expression: str, index: int, output: list[str]) -> int:
    """Copy a quoted SQL token without changing its contents.

    Args:
        expression: Source policy expression.
        index: Opening quote position.
        output: Normalized output buffer.

    Returns:
        Position immediately after the quoted token.

    Raises:
        None.
    """
    quote = expression[index]
    escaped = quote == "'" and index > 0 and expression[index - 1] in "eE"
    output.append(quote)
    index += 1
    while index < len(expression):
        char = expression[index]
        output.append(char)
        index += 1
        if escaped and char == "\\" and index < len(expression):
            output.append(expression[index])
            index += 1
        elif char == quote:
            if index < len(expression) and expression[index] == quote:
                output.append(expression[index])
                index += 1
            else:
                break
    return index


def _copy_dollar_quoted_token(
    expression: str, index: int, delimiter: str, output: list[str]
) -> int:
    """Copy a dollar-quoted SQL value without changing its contents.

    Args:
        expression: Source policy expression.
        index: Opening delimiter position.
        delimiter: Dollar quote delimiter.
        output: Normalized output buffer.

    Returns:
        Position immediately after the quoted token.

    Raises:
        None.
    """
    end = expression.find(delimiter, index + len(delimiter))
    end = len(expression) if end < 0 else end + len(delimiter)
    output.append(expression[index:end])
    return end


def _copy_sql_comment(expression: str, index: int, output: list[str]) -> int:
    """Copy a SQL comment verbatim so newline semantics remain unchanged.

    Args:
        expression: Source policy expression.
        index: Comment opening position.
        output: Normalized output buffer.

    Returns:
        Position immediately after the comment.

    Raises:
        None.
    """
    if expression.startswith("--", index):
        end = expression.find("\n", index)
        end = len(expression) if end < 0 else end + 1
        output.append(expression[index:end])
        return end
    depth = 1
    cursor = index + 2
    while cursor < len(expression) and depth:
        if expression.startswith("/*", cursor):
            depth += 1
            cursor += 2
        elif expression.startswith("*/", cursor):
            depth -= 1
            cursor += 2
        else:
            cursor += 1
    output.append(expression[index:cursor])
    return cursor


def _expected_constraint_name(item: dict[str, object]) -> str:
    """Resolve a missing ORM UNIQUE name using PostgreSQL's default naming rule.

    Args:
        item: UNIQUE or CHECK contract entry.

    Returns:
        The explicit contract name or PostgreSQL's generated UNIQUE name.

    Raises:
        ValueError: If a CHECK constraint has no explicit name.
    """
    if item["name"]:
        return str(item["name"])
    if item["kind"] != "UNIQUE":
        raise ValueError(f"Unnamed {item['kind']} constraint on {item['table']}")
    columns = "_".join(item["definition"])
    generated = f"{item['table']}_{columns}_key"
    encoded = generated.encode("utf-8")
    return encoded[:63].decode("utf-8", errors="ignore")


def _constraint_inventory_differences(expected_rows, actual_rows) -> list[str]:
    """Report missing, unexpected, and differing UNIQUE/CHECK constraint attributes.

    Args:
        expected_rows: Constraint rows from the canonical ORM contract.
        actual_rows: Constraint rows returned by PostgreSQL catalogs.

    Returns:
        Human-readable inventory differences, including expected and actual definitions.

    Raises:
        None.
    """
    expected = {
        (schema, table, name): (kind, definition)
        for schema, table, name, kind, definition in expected_rows
    }
    actual = {
        (schema, table, name): (kind, definition)
        for schema, table, name, kind, definition in actual_rows
    }
    differences = []
    for identity in sorted(expected.keys() - actual.keys()):
        kind, definition = expected[identity]
        differences.append(
            f"missing {kind} constraint {'.'.join(identity)}; expected definition={definition!r}"
        )
    for identity in sorted(actual.keys() - expected.keys()):
        kind, definition = actual[identity]
        differences.append(
            f"unexpected {kind} constraint {'.'.join(identity)}; found definition={definition!r}"
        )
    for identity in sorted(expected.keys() & actual.keys()):
        expected_kind, expected_definition = expected[identity]
        actual_kind, actual_definition = actual[identity]
        if expected_kind != actual_kind:
            differences.append(
                f"{'.'.join(identity)}: type expected={expected_kind!r} actual={actual_kind!r}; "
                f"definition expected={expected_definition!r} actual={actual_definition!r}"
            )
        elif expected_definition != actual_definition:
            differences.append(
                f"{'.'.join(identity)}: definition expected={expected_definition!r} "
                f"actual={actual_definition!r}"
            )
    return differences


def _policy_inventory_differences(expected_rows, actual_rows) -> list[str]:
    """Describe policy inventory differences while treating roles as an unordered set.

    Args:
        expected_rows: Contract rows containing identity and policy attributes.
        actual_rows: PostgreSQL catalog rows containing identity and policy attributes.

    Returns:
        Human-readable missing, unexpected, and field-level policy differences.

    Raises:
        ValueError: If duplicate policy identities appear in either inventory.
    """
    expected = _index_policy_rows(expected_rows)
    actual = _index_policy_rows(actual_rows)
    differences = [
        f"missing policy {'.'.join(identity)}"
        for identity in sorted(expected.keys() - actual.keys())
    ]
    differences.extend(
        f"unexpected policy {'.'.join(identity)}"
        for identity in sorted(actual.keys() - expected.keys())
    )
    for identity in sorted(expected.keys() & actual.keys()):
        for name, expected_value, actual_value in zip(
            _POLICY_ATTRIBUTE_NAMES, expected[identity], actual[identity], strict=True
        ):
            if expected_value != actual_value:
                policy = ".".join(identity)
                differences.append(
                    f"{policy}: {name} expected={expected_value!r} actual={actual_value!r}"
                )
    return differences


def _index_policy_rows(rows) -> dict[tuple[str, str, str], tuple[object, ...]]:
    """Index policy inventory rows by schema, table, and policy name.

    Args:
        rows: Iterable rows ordered as identity, command, roles, mode, USING, WITH CHECK.

    Returns:
        Policy attributes keyed by their catalog identity.

    Raises:
        ValueError: If an inventory contains duplicate policy identities.
    """
    indexed = {}
    for schema, table, name, command, roles, permissive, using, check in rows:
        identity = (schema, table, name)
        if identity in indexed:
            raise ValueError(f"Duplicate RLS policy identity: {'.'.join(identity)}")
        indexed[identity] = (
            command,
            tuple(sorted(roles)),
            permissive,
            _normalize_policy_expression(using),
            _normalize_policy_expression(check),
        )
    return indexed


def _sequence_default_matches(
    default: str | None,
    sequence: dict[str, object],
    references_owned_sequence: bool,
) -> bool:
    """Compare accepted PostgreSQL renderings for a schema-owned serial default.

    Args:
        default: Default expression returned by information_schema.
        sequence: Sequence contract entry, whose schema and name are verified by ownership.
        references_owned_sequence: Whether pg_depend links this default to the owned sequence OID.

    Returns:
        Whether the default references the contracted sequence.

    Raises:
        KeyError: If the sequence contract omits its schema, name, or default SQL.
    """
    unqualified = f"nextval('{sequence['name']}'::regclass)"
    return references_owned_sequence and default in {sequence["default_sql"], unqualified}


def validate_catalog(
    connection: Connection,
    *,
    expected_manifest: dict[str, str] | None = None,
    check_version: bool = False,
) -> dict[str, int]:
    from core.database import Base
    from core.model_registry import baseline_candidate_tables, register_models
    from migrations.baseline_contract import (
        BASELINE_SCHEMA,
        CHECK_CONTRACT,
        ENUM_CONTRACT,
        FK_CONTRACT,
        FUNCTION_CONTRACT,
        INDEX_CONTRACT,
        POLICY_CONTRACT,
        REQUIRED_SEQUENCE_NAMES,
        RLS_ENABLED_TABLES,
        RLS_FORCED_TABLES,
        SEQUENCE_CONTRACT,
        TRIGGER_CONTRACT,
        UNIQUE_CONTRACT,
    )

    register_models()
    expected_tables = set(baseline_candidate_tables())
    actual_tables = set(
        connection.execute(
            text("""
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms' AND c.relkind IN ('r','p')
          AND c.relname NOT IN (
              'deepfarms_install_version','alembic_version','deepfarms_install_manifest'
          )
    """)
        ).scalars()
    )
    if actual_tables != expected_tables:
        raise RuntimeError(
            "Clean-install table inventory mismatch: "
            f"missing={sorted(expected_tables - actual_tables)} "
            f"extra={sorted(actual_tables - expected_tables)}"
        )

    expected_columns = {
        (table.name, column.name, column.nullable)
        for table_name, table in Base.metadata.tables.items()
        if table_name in expected_tables
        for column in table.columns
    }
    actual_columns = set(
        map(
            tuple,
            connection.execute(
                text("""
                SELECT table_name, column_name, is_nullable = 'YES'
                FROM information_schema.columns WHERE table_schema='farms'
                  AND table_name NOT IN (
                    'deepfarms_install_version','alembic_version','deepfarms_install_manifest'
                  )
            """)
            ),
        )
    )
    if actual_columns != expected_columns:
        raise RuntimeError("Clean-install ORM column/nullability inventory mismatch")

    actual_sequences = set(
        connection.execute(
            text("""
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms' AND c.relkind='S'
    """)
        ).scalars()
    )
    if actual_sequences != set(REQUIRED_SEQUENCE_NAMES):
        raise RuntimeError(
            "Clean-install sequence inventory mismatch: "
            f"missing={sorted(set(REQUIRED_SEQUENCE_NAMES) - actual_sequences)} "
            f"extra={sorted(actual_sequences - set(REQUIRED_SEQUENCE_NAMES))}"
        )

    for sequence in SEQUENCE_CONTRACT.values():
        owned = connection.execute(
            text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
            {
                "table_name": f"farms.{sequence['owned_table']}",
                "column_name": sequence["owned_column"],
            },
        ).scalar_one_or_none()
        expected_owned = f"farms.{sequence['name']}"
        if owned != expected_owned:
            raise RuntimeError(f"Sequence ownership mismatch for {sequence['name']}")
        default = connection.execute(
            text("""
                SELECT column_default FROM information_schema.columns
                WHERE table_schema='farms' AND table_name=:table_name AND column_name=:column_name
            """),
            {"table_name": sequence["owned_table"], "column_name": sequence["owned_column"]},
        ).scalar_one_or_none()
        references_owned_sequence = connection.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_attrdef ad
                    JOIN pg_class table_rel ON table_rel.oid = ad.adrelid
                    JOIN pg_namespace table_ns ON table_ns.oid = table_rel.relnamespace
                    JOIN pg_attribute attr
                      ON attr.attrelid = table_rel.oid AND attr.attnum = ad.adnum
                    JOIN pg_depend dep
                      ON dep.classid = 'pg_attrdef'::regclass
                     AND dep.objid = ad.oid
                     AND dep.refclassid = 'pg_class'::regclass
                     AND dep.refobjid = to_regclass(:sequence_name)
                     AND dep.refobjsubid = 0
                    WHERE table_ns.nspname = 'farms'
                      AND table_rel.relname = :table_name
                      AND attr.attname = :column_name
                )
            """),
            {
                "sequence_name": expected_owned,
                "table_name": sequence["owned_table"],
                "column_name": sequence["owned_column"],
            },
        ).scalar_one()
        if not _sequence_default_matches(default, sequence, references_owned_sequence):
            raise RuntimeError(f"Sequence default mismatch for {sequence['name']}")

    rls = {
        table: (enabled, forced)
        for table, enabled, forced in connection.execute(
            text("""
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='farms' AND c.relkind IN ('r','p')
        """)
        )
    }
    if {name for name, (enabled, _) in rls.items() if enabled} != set(RLS_ENABLED_TABLES):
        raise RuntimeError("Clean-install RLS enabled-table inventory mismatch")
    if {name for name, (_, forced) in rls.items() if forced} != set(RLS_FORCED_TABLES):
        raise RuntimeError("Clean-install RLS FORCE inventory mismatch")

    actual_policies = list(connection.execute(
        text("""
        SELECT schemaname, tablename, policyname, cmd, roles, permissive, qual, with_check
        FROM pg_policies WHERE schemaname='farms'
    """)))
    expected_policies = [
        (
            row["schema"],
            row["table"],
            row["name"],
            row["command"],
            tuple(row["roles"]),
            "PERMISSIVE" if row["permissive"] else "RESTRICTIVE",
            row["using_expression"],
            row["with_check_expression"],
        )
        for row in POLICY_CONTRACT.values()
    ]
    policy_differences = _policy_inventory_differences(expected_policies, actual_policies)
    if policy_differences:
        details = "\n".join(f" - {difference}" for difference in policy_differences)
        raise RuntimeError(f"Clean-install RLS policy inventory mismatch:\n{details}")

    fk_rows = set(
        connection.execute(
            text("""
        SELECT rel.relname, con.conname FROM pg_constraint con
        JOIN pg_class rel ON rel.oid=con.conrelid
        JOIN pg_namespace n ON n.oid=con.connamespace
        WHERE n.nspname='farms' AND con.contype='f'
    """)
        )
    )
    if len(fk_rows) != len(FK_CONTRACT):
        raise RuntimeError("Clean-install foreign-key inventory mismatch")

    actual_constraints = list(
        connection.execute(
            text("""
                SELECT n.nspname, rel.relname, con.conname,
                       CASE con.contype WHEN 'u' THEN 'UNIQUE' ELSE 'CHECK' END,
                       pg_get_constraintdef(con.oid, false)
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace n ON n.oid = con.connamespace
                WHERE n.nspname = 'farms' AND con.contype IN ('u', 'c')
            """)
        )
    )
    expected_constraints = [
        (
            BASELINE_SCHEMA,
            item["table"],
            _expected_constraint_name(item),
            "UNIQUE",
            f"UNIQUE ({', '.join(item['definition'])})",
        )
        for item in UNIQUE_CONTRACT.values()
    ] + [
        (
            BASELINE_SCHEMA,
            item["table"],
            _expected_constraint_name(item),
            "CHECK",
            f"CHECK ({item['definition']})",
        )
        for item in CHECK_CONTRACT.values()
    ]
    expected_constraint_ids = {
        (schema, table, name, kind)
        for schema, table, name, kind, _ in expected_constraints
    }
    actual_constraint_ids = {
        (schema, table, name, kind)
        for schema, table, name, kind, _ in actual_constraints
    }
    unique_count = sum(kind == "UNIQUE" for _, _, _, kind, _ in actual_constraints)
    check_count = sum(kind == "CHECK" for _, _, _, kind, _ in actual_constraints)
    if (
        expected_constraint_ids != actual_constraint_ids
        or unique_count != len(UNIQUE_CONTRACT)
        or check_count != len(CHECK_CONTRACT)
    ):
        details = _constraint_inventory_differences(expected_constraints, actual_constraints)
        if unique_count != len(UNIQUE_CONTRACT):
            details.append(
                f"UNIQUE count expected={len(UNIQUE_CONTRACT)} actual={unique_count}"
            )
        if check_count != len(CHECK_CONTRACT):
            details.append(f"CHECK count expected={len(CHECK_CONTRACT)} actual={check_count}")
        raise RuntimeError(
            "Clean-install UNIQUE/CHECK constraint inventory mismatch:\n"
            + "\n".join(f" - {detail}" for detail in details)
        )

    actual_indexes = set(
        map(
            tuple,
            connection.execute(
                text("""
                SELECT table_rel.relname, index_rel.relname
                FROM pg_index idx
                JOIN pg_class table_rel ON table_rel.oid=idx.indrelid
                JOIN pg_class index_rel ON index_rel.oid=idx.indexrelid
                JOIN pg_namespace n ON n.oid=table_rel.relnamespace
                WHERE n.nspname='farms'
                  AND NOT EXISTS (
                    SELECT 1 FROM pg_constraint con
                    WHERE con.conindid=idx.indexrelid AND con.contype IN ('p','u','x')
                  )
            """)
            ),
        )
    )
    expected_indexes = {(item["table"], item["name"]) for item in INDEX_CONTRACT.values()}
    if actual_indexes != expected_indexes:
        raise RuntimeError("Clean-install ORM index inventory mismatch")

    enum_labels = {
        enum: tuple(
            connection.execute(
                text("""
            SELECT e.enumlabel FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
            JOIN pg_enum e ON e.enumtypid=t.oid WHERE n.nspname='farms' AND t.typname=:name
            ORDER BY e.enumsortorder
        """),
                {"name": enum},
            ).scalars()
        )
        for enum in ENUM_CONTRACT
    }
    if enum_labels != {name: tuple(labels) for name, labels in ENUM_CONTRACT.items()}:
        raise RuntimeError("Clean-install enum label inventory mismatch")
    actual_enum_names = set(
        connection.execute(
            text("""
        SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
        WHERE n.nspname='farms' AND t.typtype='e'
    """)
        ).scalars()
    )
    if actual_enum_names != set(ENUM_CONTRACT):
        raise RuntimeError("Clean-install enum type inventory mismatch")

    objects = set(
        map(
            tuple,
            connection.execute(
                text("""
            SELECT 'function', p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='farms'
            UNION ALL
            SELECT 'trigger', t.tgname FROM pg_trigger t
            JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='farms' AND NOT t.tgisinternal
            """)
            ),
        )
    )
    expected = {("function", name) for name in FUNCTION_CONTRACT} | {
        ("trigger", name) for name in TRIGGER_CONTRACT
    }
    if objects != expected:
        raise RuntimeError("Clean-install function/trigger inventory mismatch")

    if expected_manifest is not None:
        from clean_install.manifest import BASELINE_REVISION, INSTALL_VERSION, SEED_CONTRACT_VERSION

        manifest = connection.execute(
            text("""
                SELECT singleton, install_version, baseline_revision, baseline_sha256,
                       seed_contract_version, seed_contract_sha256
                FROM farms.deepfarms_install_manifest
            """)
        ).one_or_none()
        expected_values = (
            True,
            INSTALL_VERSION,
            BASELINE_REVISION,
            expected_manifest["baseline_sha256"],
            SEED_CONTRACT_VERSION,
            expected_manifest["seed_contract_sha256"],
        )
        if manifest != expected_values:
            raise RuntimeError("Clean-install manifest differs from pinned artifacts")

    if check_version:
        version = connection.execute(
            text("SELECT version_num FROM farms.deepfarms_install_version")
        ).scalar_one_or_none()
        if version != "deepfarms_clean_install_v1":
            raise RuntimeError("Clean-install version row missing or unexpected")
    return {
        "tables": len(actual_tables),
        "columns": len(actual_columns),
        "sequences": len(actual_sequences),
        "policies": len(actual_policies),
    }
