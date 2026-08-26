"""Align Ambiental tables with the canonical tenant-aware data model.

The original Ambiental migration used the historical ``fazenda_id`` name.
Current models use ``unidade_produtiva_id`` and the canonical
``unidades_produtivas`` table.  This migration keeps existing rows while
bringing the database constraints and RLS policies to the current contract.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_ambiental_foundation"
# The deployed database is currently stamped on this active line.  The other
# historical head is unrelated to Ambiental and must not be merged here: doing
# so makes Alembic traverse the entire legacy graph before executing this
# migration.
down_revision = "20260901_carbono_schema"
branch_labels = None
depends_on = None


AMBIENTAL_TABLES = (
    "amb_registros_car",
    "amb_alertas",
    "amb_outorgas_hidricas",
    "carbono_emissoes",
    "carbono_projetos",
    "carbono_relatorios",
)


def _table_exists(table_name: str) -> bool:
    """Return whether a table exists in the current PostgreSQL schema."""
    return sa.inspect(op.get_bind()).has_table(table_name)


def _rename_legacy_column(table_name: str) -> None:
    """Rename the legacy property column when the canonical one is absent."""
    bind = op.get_bind()
    columns = {
        column[0]
        for column in bind.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table_name"
            ),
            {"table_name": table_name},
        )
    }
    if "fazenda_id" not in columns or "unidade_produtiva_id" in columns:
        return
    bind.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" '
            'RENAME COLUMN "fazenda_id" TO "unidade_produtiva_id"'
        )
    )


def _ensure_rls(table_name: str) -> None:
    """Apply fail-closed tenant policies to a table that has tenant_id."""
    bind = op.get_bind()
    policy_prefix = f"{table_name}_tenant"
    bind.execute(sa.text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
    bind.execute(sa.text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
    for action, clause in (
        ("select", "USING (tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), ''))"),
        ("insert", "WITH CHECK (tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), ''))"),
        (
            "update",
            "USING (tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), '')) "
            "WITH CHECK (tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), ''))",
        ),
        ("delete", "USING (tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), ''))"),
    ):
        bind.execute(sa.text(f'DROP POLICY IF EXISTS {policy_prefix}_{action} ON "{table_name}"'))
        bind.execute(
            sa.text(
                f'CREATE POLICY {policy_prefix}_{action} ON "{table_name}" '
                f"FOR {action.upper()} {clause}"
            )
        )


def _ensure_tenant_unit_index(table_name: str) -> None:
    """Create the tenant/unit lookup index only when it is absent."""
    index_name = f"ix_{table_name}_tenant_unidade"
    index_names = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name in index_names:
        return
    op.create_index(index_name, table_name, ["tenant_id", "unidade_produtiva_id"], unique=False)


def _ensure_unit_foreign_key(table_name: str) -> None:
    """Replace the historical property FK only when existing values are valid."""
    bind = op.get_bind()
    legacy_name = f"{table_name}_fazenda_id_fkey"
    bind.execute(sa.text(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{legacy_name}"'))
    foreign_keys = sa.inspect(bind).get_foreign_keys(table_name)
    if any(
        fk.get("constrained_columns") == ["unidade_produtiva_id"]
        and fk.get("referred_table") == "unidades_produtivas"
        for fk in foreign_keys
    ):
        return
    if not sa.inspect(bind).has_table("unidades_produtivas"):
        return
    invalid = bind.execute(
        sa.text(
            f'SELECT count(*) FROM "{table_name}" item '
            'LEFT JOIN unidades_produtivas unidade '
            'ON unidade.id = item.unidade_produtiva_id '
            'WHERE item.unidade_produtiva_id IS NOT NULL AND unidade.id IS NULL'
        )
    ).scalar_one()
    if invalid:
        return
    op.create_foreign_key(
        f"{table_name}_unidade_produtiva_id_fkey",
        table_name,
        "unidades_produtivas",
        ["unidade_produtiva_id"],
        ["id"],
        ondelete="SET NULL",
    )


def upgrade() -> None:
    """Normalize legacy Ambiental tables and protect them with tenant RLS."""
    for table_name in ("amb_registros_car", "amb_alertas", "amb_outorgas_hidricas"):
        if _table_exists(table_name):
            _rename_legacy_column(table_name)
            if "unidade_produtiva_id" in {
                column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
            }:
                _ensure_unit_foreign_key(table_name)
                _ensure_tenant_unit_index(table_name)

    for table_name in AMBIENTAL_TABLES:
        if _table_exists(table_name):
            _ensure_rls(table_name)


def downgrade() -> None:
    """Remove only the policies and indexes introduced by this migration."""
    bind = op.get_bind()
    for table_name in AMBIENTAL_TABLES:
        if not _table_exists(table_name):
            continue
        policy_prefix = f"{table_name}_tenant"
        for action in ("select", "insert", "update", "delete"):
            bind.execute(sa.text(f'DROP POLICY IF EXISTS {policy_prefix}_{action} ON "{table_name}"'))
        bind.execute(sa.text(f'ALTER TABLE "{table_name}" NO FORCE ROW LEVEL SECURITY'))
        bind.execute(sa.text(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY'))

    for table_name in ("amb_registros_car", "amb_alertas", "amb_outorgas_hidricas"):
        if _table_exists(table_name):
            op.drop_index(f"ix_{table_name}_tenant_unidade", table_name=table_name)
