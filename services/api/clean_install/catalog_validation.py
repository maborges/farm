"""Runtime catalog gate for the clean-install snapshot; never mutates schema."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection


def validate_catalog(
    connection: Connection,
    *,
    expected_manifest: dict[str, str] | None = None,
    check_version: bool = False,
) -> dict[str, int]:
    from core.database import Base
    from core.model_registry import baseline_candidate_tables, register_models
    from migrations.baseline_contract import (
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
        if default != sequence["default_sql"]:
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

    policies = {
        (schema, table, name, command, tuple(roles), permissive, using, check)
        for schema, table, name, command, roles, permissive, using, check in connection.execute(
            text("""
        SELECT schemaname, tablename, policyname, cmd, roles, permissive, qual, with_check
        FROM pg_policies WHERE schemaname='farms'
    """)
        )
    }
    expected_policies = {
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
    }
    if policies != expected_policies:
        raise RuntimeError("Clean-install RLS policy inventory mismatch")

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

    constraint_rows = set(
        connection.execute(
            text("""
        SELECT rel.relname, con.conname, con.contype FROM pg_constraint con
        JOIN pg_class rel ON rel.oid=con.conrelid
        JOIN pg_namespace n ON n.oid=con.connamespace
        WHERE n.nspname='farms' AND con.contype IN ('u','c')
    """)
        )
    )
    expected_unique = {(item["table"], item["name"], "u") for item in UNIQUE_CONTRACT.values()}
    expected_checks = {(item["table"], item["name"], "c") for item in CHECK_CONTRACT.values()}
    if not (expected_unique | expected_checks).issubset(constraint_rows):
        raise RuntimeError("Clean-install UNIQUE/CHECK constraint inventory mismatch")
    if len([row for row in constraint_rows if row[2] == "u"]) != len(UNIQUE_CONTRACT):
        raise RuntimeError("Clean-install UNIQUE constraint count mismatch")
    if len([row for row in constraint_rows if row[2] == "c"]) != len(CHECK_CONTRACT):
        raise RuntimeError("Clean-install CHECK constraint count mismatch")

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
        "policies": len(policies),
    }
