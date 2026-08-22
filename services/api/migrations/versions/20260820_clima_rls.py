"""Enable tenant isolation for climate observations and forecasts."""

from alembic import op
import sqlalchemy as sa


revision = "20260820_clima_rls"
down_revision = "20260820_clima_idempotency"
branch_labels = None
depends_on = None


TENANT_EXPR = "current_setting('app.current_tenant_id', true)::uuid"


def _enable_tenant_rls(table_name: str, policy_prefix: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    for action in ("select", "insert", "update", "delete"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_{action}_tenant ON {table_name}"))

    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant ON {table_name}
            FOR SELECT
            USING (tenant_id = {TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant ON {table_name}
            FOR INSERT
            WITH CHECK (tenant_id = {TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant ON {table_name}
            FOR UPDATE
            USING (tenant_id = {TENANT_EXPR})
            WITH CHECK (tenant_id = {TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_delete_tenant ON {table_name}
            FOR DELETE
            USING (tenant_id = {TENANT_EXPR})
            """
        )
    )


def upgrade() -> None:
    _enable_tenant_rls("registros_clima", "registros_clima")
    _enable_tenant_rls("previsoes_clima", "previsoes_clima")


def downgrade() -> None:
    for table_name, policy_prefix in (
        ("previsoes_clima", "previsoes_clima"),
        ("registros_clima", "registros_clima"),
    ):
        for action in ("select", "insert", "update", "delete"):
            op.execute(
                sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_{action}_tenant ON {table_name}")
            )
        op.execute(sa.text(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
