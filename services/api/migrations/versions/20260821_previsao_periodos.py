"""Store intraday forecast periods alongside daily forecast summaries."""

from alembic import op
import sqlalchemy as sa


revision = "20260821_previsao_periodos"
down_revision = "20260820_operational_alerts_rls_safe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "previsoes_clima",
        sa.Column("periodos", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("previsoes_clima", "periodos")
