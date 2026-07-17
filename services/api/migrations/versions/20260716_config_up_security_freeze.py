"""security freeze for configuracao_fazenda by unidade produtiva

Revision ID: 20260716_config_up_security_freeze
Revises: 265b28773962
Create Date: 2026-07-16 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260716_config_up_security_freeze"
down_revision = "265b28773962"
branch_labels = None
depends_on = None


TABLE_NAME = "configuracao_fazenda"
UP_TABLE = "unidades_produtivas"


def _tenant_rls(table_name: str) -> None:
    policy_prefix = table_name.replace(".", "_")
    op.execute(sa.text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
    for action, clause in (
        ("select", "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"),
        ("insert", "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"),
        (
            "update",
            "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid) "
            "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)",
        ),
        ("delete", "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"),
    ):
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {policy_prefix}_{action}_tenant
                ON "{table_name}"
                FOR {action.upper()}
                {clause}
                """
            )
        )


def _drop_tenant_rls(table_name: str) -> None:
    policy_prefix = table_name.replace(".", "_")
    for action in ("delete", "update", "insert", "select"):
        op.execute(sa.text(f'DROP POLICY IF EXISTS {policy_prefix}_{action}_tenant ON "{table_name}"'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY'))


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_unidades_produtivas_tenant_id_id",
        UP_TABLE,
        ["tenant_id", "id"],
    )
    op.create_foreign_key(
        "fk_configuracao_fazenda_tenant_unidade_produtiva",
        TABLE_NAME,
        UP_TABLE,
        ["tenant_id", "unidade_produtiva_id"],
        ["tenant_id", "id"],
        ondelete="CASCADE",
    )
    _tenant_rls(TABLE_NAME)


def downgrade() -> None:
    _drop_tenant_rls(TABLE_NAME)
    op.drop_constraint(
        "fk_configuracao_fazenda_tenant_unidade_produtiva",
        TABLE_NAME,
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_unidades_produtivas_tenant_id_id",
        UP_TABLE,
        type_="unique",
    )
