"""add recomendado_pela_ia to financeiro_safra_cenarios

Revision ID: 20260508_recomendado_ia
Revises: 20260508_campo_pwa_05
Create Date: 2026-05-08
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260508_recomendado_ia"
down_revision: Union[str, Sequence[str], None] = "20260508_campo_pwa_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "financeiro_safra_cenarios",
        sa.Column("recomendado_pela_ia", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_column("financeiro_safra_cenarios", "recomendado_pela_ia")
