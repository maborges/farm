"""add_compras_solicitacoes

Revision ID: c978b1800b4c
Revises: 9e1e52776dd0
Create Date: 2026-05-03 02:22:18.512627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c978b1800b4c'
down_revision: Union[str, Sequence[str], None] = '9e1e52776dd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'compras_solicitacoes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('produto_id', sa.Uuid(), nullable=False),
        sa.Column('deposito_id', sa.Uuid(), nullable=False),
        sa.Column('quantidade_solicitada', sa.Float(), nullable=False),
        sa.Column('unidade', sa.String(length=20), nullable=False),
        sa.Column('origem', sa.String(length=30), nullable=False),
        sa.Column('origem_id', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['deposito_id'], ['estoque_depositos.id'], ),
        sa.ForeignKeyConstraint(['produto_id'], ['cadastros_produtos.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compras_solicitacoes_deposito_id'), 'compras_solicitacoes', ['deposito_id'], unique=False)
    op.create_index(op.f('ix_compras_solicitacoes_produto_id'), 'compras_solicitacoes', ['produto_id'], unique=False)
    op.create_index(op.f('ix_compras_solicitacoes_status'), 'compras_solicitacoes', ['status'], unique=False)
    op.create_index(op.f('ix_compras_solicitacoes_tenant_id'), 'compras_solicitacoes', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_compras_solicitacoes_tenant_id'), table_name='compras_solicitacoes')
    op.drop_index(op.f('ix_compras_solicitacoes_status'), table_name='compras_solicitacoes')
    op.drop_index(op.f('ix_compras_solicitacoes_produto_id'), table_name='compras_solicitacoes')
    op.drop_index(op.f('ix_compras_solicitacoes_deposito_id'), table_name='compras_solicitacoes')
    op.drop_table('compras_solicitacoes')
