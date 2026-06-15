"""create_hedge_position_snapshot

Revision ID: ff59b3b71a2d
Revises: hedge_mvp_merge_001
Create Date: 2026-06-14 23:38:26.718567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff59b3b71a2d'
down_revision: Union[str, Sequence[str], None] = 'hedge_mvp_merge_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('hedge_position_snapshots_v2',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('contrato_futuro_id', sa.UUID(), nullable=False),
        sa.Column('safra_id', sa.UUID(), nullable=True),
        sa.Column('commodity_id', sa.UUID(), nullable=True),
        sa.Column('data_referencia', sa.Date(), nullable=False),
        sa.Column('quantidade_aberta', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('preco_contratado', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('preco_mercado', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('moeda', sa.String(length=3), nullable=False, server_default='BRL'),
        sa.Column('unidade', sa.String(length=20), nullable=False, server_default='sc'),
        sa.Column('mtm_valor', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('pnl_nao_realizado', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('fonte_preco', sa.String(length=50), nullable=True),
        sa.Column('calculado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['commodity_id'], ['cadastros_commodities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['contrato_futuro_id'], ['contratos_futuros_v2.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['safra_id'], ['safras.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_hedge_snapshot_tenant_safra', 'hedge_position_snapshots_v2', ['tenant_id', 'safra_id'], unique=False)
    op.create_index('uq_hedge_snapshot_tenant_contrato_data', 'hedge_position_snapshots_v2', ['tenant_id', 'contrato_futuro_id', 'data_referencia'], unique=True)
    op.create_index(op.f('ix_hedge_position_snapshots_v2_commodity_id'), 'hedge_position_snapshots_v2', ['commodity_id'], unique=False)
    op.create_index(op.f('ix_hedge_position_snapshots_v2_contrato_futuro_id'), 'hedge_position_snapshots_v2', ['contrato_futuro_id'], unique=False)
    op.create_index(op.f('ix_hedge_position_snapshots_v2_data_referencia'), 'hedge_position_snapshots_v2', ['data_referencia'], unique=False)
    op.create_index(op.f('ix_hedge_position_snapshots_v2_safra_id'), 'hedge_position_snapshots_v2', ['safra_id'], unique=False)
    op.create_index(op.f('ix_hedge_position_snapshots_v2_tenant_id'), 'hedge_position_snapshots_v2', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('hedge_position_snapshots_v2')
