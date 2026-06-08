"""create_equipamento_calibracao

Revision ID: 2325278cb390
Revises: a4dc0640fdcf
Create Date: 2026-06-07 14:10:36.264074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2325278cb390'
down_revision: Union[str, Sequence[str], None] = 'a4dc0640fdcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'cadastros_equipamentos_calibracoes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('equipamento_id', sa.Uuid(), nullable=False),
        sa.Column('data_calibracao', sa.Date(), nullable=False),
        sa.Column('validade_ate', sa.Date(), nullable=False),
        sa.Column('metodo', sa.String(length=200), nullable=False),
        sa.Column('vazao', sa.Float(), nullable=False),
        sa.Column('pressao', sa.Float(), nullable=False),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('hash_documental', sa.String(length=64), nullable=False),
        sa.Column('criado_por', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['equipamento_id'], ['cadastros_equipamentos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cad_equip_calib_tenant_id', 'cadastros_equipamentos_calibracoes', ['tenant_id'], unique=False)
    op.create_index('ix_cad_equip_calib_equipamento_id', 'cadastros_equipamentos_calibracoes', ['equipamento_id'], unique=False)
    op.create_index('ix_cad_equip_calib_data_calibracao', 'cadastros_equipamentos_calibracoes', ['data_calibracao'], unique=False)
    op.create_index('ix_cad_equip_calib_validade_ate', 'cadastros_equipamentos_calibracoes', ['validade_ate'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_cad_equip_calib_validade_ate', table_name='cadastros_equipamentos_calibracoes')
    op.drop_index('ix_cad_equip_calib_data_calibracao', table_name='cadastros_equipamentos_calibracoes')
    op.drop_index('ix_cad_equip_calib_equipamento_id', table_name='cadastros_equipamentos_calibracoes')
    op.drop_index('ix_cad_equip_calib_tenant_id', table_name='cadastros_equipamentos_calibracoes')
    op.drop_table('cadastros_equipamentos_calibracoes')
