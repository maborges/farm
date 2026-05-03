"""create_compras_cotacoes_table

Revision ID: d59f78311bad
Revises: c978b1800b4c
Create Date: 2026-05-03 03:09:33.470315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd59f78311bad'
down_revision: Union[str, Sequence[str], None] = 'c978b1800b4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Renomear tabela antiga para evitar conflito
    op.rename_table('compras_cotacoes', 'compras_pedidos_cotacoes')
    
    # 2. Criar nova tabela de cotações vinculada a solicitações
    op.create_table(
        'compras_cotacoes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('solicitacao_id', sa.Uuid(), nullable=False),
        sa.Column('fornecedor_nome', sa.String(length=150), nullable=False),
        sa.Column('fornecedor_contato', sa.String(length=150), nullable=True),
        sa.Column('valor_unitario', sa.Float(), nullable=False),
        sa.Column('valor_total', sa.Float(), nullable=False),
        sa.Column('prazo_entrega_dias', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='RECEBIDA'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['solicitacao_id'], ['compras_solicitacoes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compras_cotacoes_solicitacao_id'), 'compras_cotacoes', ['solicitacao_id'], unique=False)
    op.create_index(op.f('ix_compras_cotacoes_status'), 'compras_cotacoes', ['status'], unique=False)
    op.create_index(op.f('ix_compras_cotacoes_tenant_id'), 'compras_cotacoes', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_compras_cotacoes_tenant_id'), table_name='compras_cotacoes')
    op.drop_index(op.f('ix_compras_cotacoes_status'), table_name='compras_cotacoes')
    op.drop_index(op.f('ix_compras_cotacoes_solicitacao_id'), table_name='compras_cotacoes')
    op.drop_table('compras_cotacoes')
    
    # Restaurar tabela antiga
    op.rename_table('compras_pedidos_cotacoes', 'compras_cotacoes')
