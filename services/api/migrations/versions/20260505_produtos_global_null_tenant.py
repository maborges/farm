"""allow global cadastros_produtos records

Revision ID: 20260505_produtos_global
Revises: 20260505_notif_cols
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260505_produtos_global"
down_revision = "20260505_notif_cols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cadastros_produtos", schema=None) as batch_op:
        batch_op.alter_column(
            "tenant_id",
            existing_type=sa.Uuid(),
            nullable=True,
            existing_nullable=False,
            comment="NULL = produto padrao do sistema",
        )


def downgrade() -> None:
    with op.batch_alter_table("cadastros_produtos", schema=None) as batch_op:
        batch_op.alter_column(
            "tenant_id",
            existing_type=sa.Uuid(),
            nullable=False,
            existing_nullable=True,
        )
