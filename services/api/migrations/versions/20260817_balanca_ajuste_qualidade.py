"""balanca ajuste de qualidade (desconto pos-pesagem) + numero_documento_fiscal via scan

Revision ID: 20260817_balanca_ajuste_qualidade
Revises: 20260817_balanca_fisica_afericao
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260817_balanca_ajuste_qualidade"
down_revision = "20260817_balanca_fisica_afericao"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("balanca_ordens", sa.Column("desconto_percentual", sa.Numeric(5, 2), nullable=True))
    op.add_column("balanca_ordens", sa.Column("desconto_motivo", sa.Text, nullable=True))
    op.add_column("balanca_ordens", sa.Column("peso_liquido_comercial_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("balanca_ordens", sa.Column("ajuste_aplicado_em", sa.DateTime, nullable=True))
    op.add_column("balanca_ordens", sa.Column("ajuste_aplicado_por", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("COMMIT")


def downgrade():
    op.drop_column("balanca_ordens", "ajuste_aplicado_por")
    op.drop_column("balanca_ordens", "ajuste_aplicado_em")
    op.drop_column("balanca_ordens", "peso_liquido_comercial_kg")
    op.drop_column("balanca_ordens", "desconto_motivo")
    op.drop_column("balanca_ordens", "desconto_percentual")
    op.execute("COMMIT")
