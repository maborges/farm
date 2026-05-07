"""stepGrowth22 — Governanca e aprovacao de incentivos (IA-Growth-22)

Adiciona a camada de aprovacao humana para incentivos sensiveis,
permitindo que ofertas controladas sejam revisadas antes da liberacao.

Revision ID: stepGrowth22
Revises: stepGrowth21
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa

revision = "stepGrowth22"
down_revision = "stepGrowth21"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ia_growth_incentivos", sa.Column("aprovado_por", sa.Uuid(as_uuid=True), nullable=True))
    op.add_column("ia_growth_incentivos", sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ia_growth_incentivos", sa.Column("motivo_reprovacao", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("ia_growth_incentivos", "motivo_reprovacao")
    op.drop_column("ia_growth_incentivos", "aprovado_em")
    op.drop_column("ia_growth_incentivos", "aprovado_por")
