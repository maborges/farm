"""stepGrowth20 — Tipos de oferta e performance de ofertas (IA-Growth-20)

Adiciona classificação de oferta ao log de plano recomendado para permitir
análise de conversão, distribuição e impacto por abordagem comercial.

Revision ID: stepGrowth20
Revises: stepGrowth19
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "stepGrowth20"
down_revision = "stepGrowth19"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ia_growth_plano_recomendado_log", sa.Column("tipo_oferta", sa.String(length=30), nullable=True))
    op.add_column("ia_growth_plano_recomendado_log", sa.Column("mensagem_oferta", sa.Text(), nullable=True))
    op.add_column("ia_growth_plano_recomendado_log", sa.Column("beneficio_destacado", sa.String(length=200), nullable=True))
    op.create_index(
        "ix_iagrowth_plano_rec_oferta",
        "ia_growth_plano_recomendado_log",
        ["tenant_id", "tipo_oferta", "exibida_em"],
    )


def downgrade():
    op.drop_index("ix_iagrowth_plano_rec_oferta", table_name="ia_growth_plano_recomendado_log")
    op.drop_column("ia_growth_plano_recomendado_log", "beneficio_destacado")
    op.drop_column("ia_growth_plano_recomendado_log", "mensagem_oferta")
    op.drop_column("ia_growth_plano_recomendado_log", "tipo_oferta")
