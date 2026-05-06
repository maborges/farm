"""stepGrowth15_ia_growth_churn_tracking

Revision ID: 7a1c2f9d4e31
Revises: 0f302ce22c97
Create Date: 2026-05-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a1c2f9d4e31"
down_revision: Union[str, Sequence[str], None] = "0f302ce22c97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("ia_growth_eventos", sa.Column("churn_risk_score", sa.Float(), nullable=True))
    op.add_column("ia_growth_eventos", sa.Column("churn_risk_level", sa.String(length=10), nullable=True))
    op.create_index(
        "ix_ia_growth_churn_level",
        "ia_growth_eventos",
        ["tenant_id", "churn_risk_level", "created_at"],
        unique=False,
    )

    op.add_column("ia_growth_experimento_eventos", sa.Column("churn_risk_score", sa.Float(), nullable=True))
    op.add_column("ia_growth_experimento_eventos", sa.Column("churn_risk_level", sa.String(length=10), nullable=True))
    op.create_index(
        "ix_ia_growth_exp_eventos_churn",
        "ia_growth_experimento_eventos",
        ["tenant_id", "churn_risk_level", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_ia_growth_exp_eventos_churn", table_name="ia_growth_experimento_eventos")
    op.drop_column("ia_growth_experimento_eventos", "churn_risk_level")
    op.drop_column("ia_growth_experimento_eventos", "churn_risk_score")

    op.drop_index("ix_ia_growth_churn_level", table_name="ia_growth_eventos")
    op.drop_column("ia_growth_eventos", "churn_risk_level")
    op.drop_column("ia_growth_eventos", "churn_risk_score")
