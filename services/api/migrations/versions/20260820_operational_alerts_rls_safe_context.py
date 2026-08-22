"""Make operational alert RLS fail closed on an empty tenant context."""

from alembic import op
import sqlalchemy as sa


revision = "20260820_operational_alerts_rls_safe"
down_revision = "20260820_alerts_integrations_domain"
branch_labels = None
depends_on = None


TABLE_NAME = "operational_alerts"
POLICY_PREFIX = "operational_alerts"
TENANT_EXPR = "tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), '')"


def upgrade() -> None:
    for action in ("select", "insert", "update", "delete"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {POLICY_PREFIX}_{action}_tenant ON {TABLE_NAME}"))

    op.execute(sa.text(f"""
        CREATE POLICY {POLICY_PREFIX}_select_tenant ON {TABLE_NAME}
        FOR SELECT USING ({TENANT_EXPR})
    """))
    op.execute(sa.text(f"""
        CREATE POLICY {POLICY_PREFIX}_insert_tenant ON {TABLE_NAME}
        FOR INSERT WITH CHECK ({TENANT_EXPR})
    """))
    op.execute(sa.text(f"""
        CREATE POLICY {POLICY_PREFIX}_update_tenant ON {TABLE_NAME}
        FOR UPDATE USING ({TENANT_EXPR}) WITH CHECK ({TENANT_EXPR})
    """))
    op.execute(sa.text(f"""
        CREATE POLICY {POLICY_PREFIX}_delete_tenant ON {TABLE_NAME}
        FOR DELETE USING ({TENANT_EXPR})
    """))


def downgrade() -> None:
    previous_expr = "tenant_id = current_setting('app.current_tenant_id', true)::uuid"
    for action in ("select", "insert", "update", "delete"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {POLICY_PREFIX}_{action}_tenant ON {TABLE_NAME}"))
    op.execute(sa.text(f"""
        CREATE POLICY {POLICY_PREFIX}_select_tenant ON {TABLE_NAME}
        FOR SELECT USING ({previous_expr})
    """))
    op.execute(sa.text(f"""
        CREATE POLICY {POLICY_PREFIX}_insert_tenant ON {TABLE_NAME}
        FOR INSERT WITH CHECK ({previous_expr})
    """))
    op.execute(sa.text(f"""
        CREATE POLICY {POLICY_PREFIX}_update_tenant ON {TABLE_NAME}
        FOR UPDATE USING ({previous_expr}) WITH CHECK ({previous_expr})
    """))
    op.execute(sa.text(f"""
        CREATE POLICY {POLICY_PREFIX}_delete_tenant ON {TABLE_NAME}
        FOR DELETE USING ({previous_expr})
    """))
