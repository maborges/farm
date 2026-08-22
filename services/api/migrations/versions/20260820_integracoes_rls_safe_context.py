"""Prevent empty tenant RLS context errors for integration configuration."""

from alembic import op
import sqlalchemy as sa


revision = "20260820_integracoes_rls_safe"
down_revision = "20260820_clima_rls_safe"
branch_labels = None
depends_on = None


TENANT_EXPR = "tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), '')"
POLICY_PREFIX = "farms_tenant_integracoes"
TABLE_NAME = "tenant_integracoes"


def _recreate_policies() -> None:
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


def upgrade() -> None:
    _recreate_policies()


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
