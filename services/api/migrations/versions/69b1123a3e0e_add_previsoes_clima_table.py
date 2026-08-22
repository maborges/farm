"""add previsoes_clima table

Revision ID: 69b1123a3e0e
Revises: 20260818_clima_escopo_unidade
Create Date: 2026-08-19 16:50:17.294052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69b1123a3e0e'
down_revision: Union[str, Sequence[str], None] = '20260818_clima_escopo_unidade'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('previsoes_clima',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('unidade_produtiva_id', sa.Uuid(), nullable=False),
    sa.Column('data_previsao', sa.Date(), nullable=False),
    sa.Column('precipitacao_mm', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('temp_max_c', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('temp_min_c', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('probabilidade_chuva_pct', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['unidade_produtiva_id'], ['unidades_produtivas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('previsoes_clima', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_previsoes_clima_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_previsoes_clima_unidade_produtiva_id'), ['unidade_produtiva_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('previsoes_clima', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_previsoes_clima_unidade_produtiva_id'))
        batch_op.drop_index(batch_op.f('ix_previsoes_clima_tenant_id'))

    op.drop_table('previsoes_clima')
