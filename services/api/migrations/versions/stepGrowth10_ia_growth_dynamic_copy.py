"""stepGrowth10 — Dynamic copy for growth experiments (Growth-10)

Revision ID: stepGrowth10
Revises: stepGrowth08
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "stepGrowth10"
down_revision = "stepGrowth08"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ia_growth_experimento_variantes", sa.Column("cta", JSONB(), nullable=True))


def downgrade():
    op.drop_column("ia_growth_experimento_variantes", "cta")
