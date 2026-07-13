"""integrations tenant integracao unique indexes

Revision ID: 20260712_integrations_tenant_integracao_unique_indexes
Revises: f1dfe22c7fa5
Create Date: 2026-07-12 12:00:00.000000
"""

# ruff: noqa: E501, S608, I001

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_integrations_tenant_integracao_unique_indexes"
down_revision = "f1dfe22c7fa5"
branch_labels = None
depends_on = None


SCHEMA = "farms"
TABLE = "tenant_integracoes"
TENANT_INDEX = "uq_tenant_integracoes_provider_scope_tenant"
ESTAB_INDEX = "uq_tenant_integracoes_provider_scope_estabelecimento"

TENANT_PREDICATE = """
    scope_type = 'TENANT'
    AND scope_id IS NULL
    AND deleted_at IS NULL
"""

ESTAB_PREDICATE = """
    scope_type = 'ESTABELECIMENTO'
    AND scope_id IS NOT NULL
    AND deleted_at IS NULL
"""


def _dialect_name() -> str:
    bind = op.get_bind()
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", "")


def _qualify(table_name: str) -> str:
    return f"{SCHEMA}.{table_name}"


def _count_blocking_duplicates(predicate: str, columns: list[str]) -> int:
    columns_sql = ", ".join(columns)
    stmt = sa.text(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {columns_sql}, COUNT(*) AS qty
            FROM {_qualify(TABLE)}
            WHERE {predicate}
            GROUP BY {columns_sql}
            HAVING COUNT(*) > 1
        ) AS dup
        """
    )
    return int(op.get_bind().execute(stmt).scalar_one())


def _count_invalid_scope_rows() -> tuple[int, int]:
    tenant_stmt = sa.text(
        f"""
        SELECT COUNT(*)
        FROM {_qualify(TABLE)}
        WHERE scope_type = 'TENANT'
          AND scope_id IS NOT NULL
          AND deleted_at IS NULL
        """
    )
    estab_stmt = sa.text(
        f"""
        SELECT COUNT(*)
        FROM {_qualify(TABLE)}
        WHERE scope_type = 'ESTABELECIMENTO'
          AND scope_id IS NULL
          AND deleted_at IS NULL
        """
    )
    bind = op.get_bind()
    return int(bind.execute(tenant_stmt).scalar_one()), int(bind.execute(estab_stmt).scalar_one())


def _index_state(index_name: str) -> tuple[bool, bool]:
    if _dialect_name() != "postgresql":
        return False, False

    stmt = sa.text(
        """
        SELECT
            EXISTS (
                SELECT 1
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = :schema
                  AND c.relname = :index_name
                  AND c.relkind = 'i'
            ) AS exists,
            COALESCE(
                (
                    SELECT i.indisvalid
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    JOIN pg_index i ON i.indexrelid = c.oid
                    WHERE n.nspname = :schema
                      AND c.relname = :index_name
                      AND c.relkind = 'i'
                ),
                false
            ) AS valid
        """
    )
    row = op.get_bind().execute(stmt, {"schema": SCHEMA, "index_name": index_name}).one()
    return bool(row[0]), bool(row[1])


def _abort_if_blockers_found() -> None:
    tenant_dups = _count_blocking_duplicates(TENANT_PREDICATE, ["tenant_id", "integracao_id"])
    estab_dups = _count_blocking_duplicates(
        ESTAB_PREDICATE,
        ["tenant_id", "integracao_id", "scope_id"],
    )
    invalid_tenant_rows, invalid_estab_rows = _count_invalid_scope_rows()

    blockers: list[str] = []
    if tenant_dups:
        blockers.append(f"duplicidade TENANT: {tenant_dups}")
    if estab_dups:
        blockers.append(f"duplicidade ESTABELECIMENTO: {estab_dups}")
    if invalid_tenant_rows:
        blockers.append(f"registros TENANT com scope_id preenchido: {invalid_tenant_rows}")
    if invalid_estab_rows:
        blockers.append(f"registros ESTABELECIMENTO com scope_id nulo: {invalid_estab_rows}")

    if blockers:
        raise RuntimeError(
            "Não foi possível criar a unicidade física de tenant_integracoes. "
            + " | ".join(blockers)
        )


def _create_index_concurrently(index_name: str, ddl: str) -> None:
    dialect = _dialect_name()

    if dialect == "postgresql":
        exists, valid = _index_state(index_name)
        if exists and valid:
            return
        bind = op.get_bind()
        if bind.in_transaction():
            bind.commit()
        if exists and not valid:
            with op.get_context().autocommit_block():
                op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}"))
        with op.get_context().autocommit_block():
            op.execute(sa.text(ddl))
        return

    # SQLite e outros dialetos de teste: cria índice parcial sem CONCURRENTLY.
    if dialect == "sqlite":
        if index_name == TENANT_INDEX:
            op.create_index(
                index_name,
                TABLE,
                ["tenant_id", "integracao_id"],
                unique=True,
                sqlite_where=sa.text("scope_type = 'TENANT' AND scope_id IS NULL AND deleted_at IS NULL"),
            )
        elif index_name == ESTAB_INDEX:
            op.create_index(
                index_name,
                TABLE,
                ["tenant_id", "integracao_id", "scope_id"],
                unique=True,
                sqlite_where=sa.text(
                    "scope_type = 'ESTABELECIMENTO' AND scope_id IS NOT NULL AND deleted_at IS NULL"
                ),
            )
        return

    op.execute(sa.text(ddl))


def _drop_index_concurrently(index_name: str) -> None:
    dialect = _dialect_name()
    if dialect == "postgresql":
        exists, valid = _index_state(index_name)
        if not exists:
            return
        bind = op.get_bind()
        if bind.in_transaction():
            bind.commit()
        with op.get_context().autocommit_block():
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}"))
        return

    if dialect == "sqlite":
        op.drop_index(index_name, table_name=TABLE)
        return

    op.execute(sa.text(f"DROP INDEX IF EXISTS {SCHEMA}.{index_name}"))


def upgrade() -> None:
    _abort_if_blockers_found()

    _create_index_concurrently(
        TENANT_INDEX,
        f"""
        CREATE UNIQUE INDEX CONCURRENTLY {TENANT_INDEX}
        ON {SCHEMA}.{TABLE} (tenant_id, integracao_id)
        WHERE scope_type = 'TENANT'
          AND scope_id IS NULL
          AND deleted_at IS NULL
        """,
    )

    _create_index_concurrently(
        ESTAB_INDEX,
        f"""
        CREATE UNIQUE INDEX CONCURRENTLY {ESTAB_INDEX}
        ON {SCHEMA}.{TABLE} (tenant_id, integracao_id, scope_id)
        WHERE scope_type = 'ESTABELECIMENTO'
          AND scope_id IS NOT NULL
          AND deleted_at IS NULL
        """,
    )


def downgrade() -> None:
    _drop_index_concurrently(ESTAB_INDEX)
    _drop_index_concurrently(TENANT_INDEX)
