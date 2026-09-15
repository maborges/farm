"""Importação e conferência de documentos fiscais, sem emissão."""
from alembic import op
import sqlalchemy as sa

revision = '20260914_documentos_fiscais'
down_revision = '20260913_repair_estoque_movimentos_origem'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('fin_notas_fiscais', sa.Column('gestao', sa.JSON(), nullable=True))
    op.add_column('fin_notas_fiscais', sa.Column('xml_original', sa.LargeBinary(), nullable=True))


def downgrade():
    op.drop_column('fin_notas_fiscais', 'xml_original')
    op.drop_column('fin_notas_fiscais', 'gestao')
