"""optimize_frota_performance_indexes

Revision ID: ddaa3c59131c
Revises: 20260507_growth_landing
Create Date: 2026-05-08 00:02:51.350273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ddaa3c59131c'
down_revision: Union[str, Sequence[str], None] = '20260507_growth_landing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # frota_abastecimentos (index only)
    with op.batch_alter_table('frota_abastecimentos', schema=None) as batch_op:
        batch_op.create_index('ix_frota_abast_tenant_equip_data', ['tenant_id', 'equipamento_id', 'data'], unique=False)

    # frota_jornadas_equipamento (indices only)
    with op.batch_alter_table('frota_jornadas_equipamento', schema=None) as batch_op:
        batch_op.create_index('ix_frota_jornadas_tenant_equip_data', ['tenant_id', 'equipamento_id', 'data_inicio'], unique=False)
        batch_op.create_index('ix_frota_jornadas_tenant_safra', ['tenant_id', 'safra_id'], unique=False)

    # frota_ordens_servico (index only)
    with op.batch_alter_table('frota_ordens_servico', schema=None) as batch_op:
        batch_op.create_index('ix_frota_os_tenant_equip_status', ['tenant_id', 'equipamento_id', 'status'], unique=False)

    # frota_planos_manutencao (ADD tenant_id + index)
    with op.batch_alter_table('frota_planos_manutencao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tenant_id', sa.Uuid(), nullable=True))
    
    # Update existing records if any (placeholder or real tenant)
    # op.execute("UPDATE frota_planos_manutencao SET tenant_id = '...' WHERE tenant_id IS NULL")
    
    with op.batch_alter_table('frota_planos_manutencao', schema=None) as batch_op:
        batch_op.create_index('ix_frota_planos_tenant_equip', ['tenant_id', 'equipamento_id'], unique=False)
        batch_op.create_foreign_key('frota_planos_tenant_fk', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    # frota_registros_manutencao (ADD tenant_id + index)
    with op.batch_alter_table('frota_registros_manutencao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tenant_id', sa.Uuid(), nullable=True))

    with op.batch_alter_table('frota_registros_manutencao', schema=None) as batch_op:
        batch_op.create_index('ix_frota_reg_manut_tenant_equip_data', ['tenant_id', 'equipamento_id', 'data_realizacao'], unique=False)
        batch_op.create_foreign_key('frota_registros_tenant_fk', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    with op.batch_alter_table('frota_registros_manutencao', schema=None) as batch_op:
        batch_op.drop_constraint('frota_registros_tenant_fk', type_='foreignkey')
        batch_op.drop_index('ix_frota_reg_manut_tenant_equip_data')
        batch_op.drop_column('tenant_id')

    with op.batch_alter_table('frota_planos_manutencao', schema=None) as batch_op:
        batch_op.drop_constraint('frota_planos_tenant_fk', type_='foreignkey')
        batch_op.drop_index('ix_frota_planos_tenant_equip')
        batch_op.drop_column('tenant_id')

    with op.batch_alter_table('frota_ordens_servico', schema=None) as batch_op:
        batch_op.drop_index('ix_frota_os_tenant_equip_status')

    with op.batch_alter_table('frota_jornadas_equipamento', schema=None) as batch_op:
        batch_op.drop_index('ix_frota_jornadas_tenant_safra')
        batch_op.drop_index('ix_frota_jornadas_tenant_equip_data')

    with op.batch_alter_table('frota_abastecimentos', schema=None) as batch_op:
        batch_op.drop_index('ix_frota_abast_tenant_equip_data')
