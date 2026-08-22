"""Make climate RLS fail closed when the tenant context is empty or malformed."""

from alembic import op
import sqlalchemy as sa


revision = "20260820_clima_rls_safe"
down_revision = "20260820_clima_rls"
branch_labels = None
depends_on = None


# Comparing as text avoids casting an empty/malformed setting to UUID.  A missing
# or invalid context therefore returns no rows instead of breaking the request.
TENANT_EXPR = "tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), '')"


def _recreate_policies(table_name: str, policy_prefix: str) -> None:
    for action in ("select", "insert", "update", "delete"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_{action}_tenant ON {table_name}"))

    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant ON {table_name}
            FOR SELECT
            USING ({TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant ON {table_name}
            FOR INSERT
            WITH CHECK ({TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant ON {table_name}
            FOR UPDATE
            USING ({TENANT_EXPR})
            WITH CHECK ({TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_delete_tenant ON {table_name}
            FOR DELETE
            USING ({TENANT_EXPR})
            """
        )
    )


def upgrade() -> None:
    _recreate_policies("registros_clima", "registros_clima")
    _recreate_policies("previsoes_clima", "previsoes_clima")


def downgrade() -> None:
    # Restore the previous policy definition; the preceding migration owns the
    # RLS lifecycle and will remove these policies on downgrade.
    previous_expr = "tenant_id = current_setting('app.current_tenant_id', true)::uuid"
    for table_name, policy_prefix in (
        ("registros_clima", "registros_clima"),
        ("previsoes_clima", "previsoes_clima"),
    ):
        for action in ("select", "insert", "update", "delete"):
            op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_{action}_tenant ON {table_name}"))
        op.execute(sa.text(f"""
            CREATE POLICY {policy_prefix}_select_tenant ON {table_name}
            FOR SELECT USING ({previous_expr})
        """))
        op.execute(sa.text(f"""
            CREATE POLICY {policy_prefix}_insert_tenant ON {table_name}
            FOR INSERT WITH CHECK ({previous_expr})
        """))
        op.execute(sa.text(f"""
            CREATE POLICY {policy_prefix}_update_tenant ON {table_name}
            FOR UPDATE USING ({previous_expr}) WITH CHECK ({previous_expr})
        """))
        op.execute(sa.text(f"""
            CREATE POLICY {policy_prefix}_delete_tenant ON {table_name}
            FOR DELETE USING ({previous_expr})
        """))
