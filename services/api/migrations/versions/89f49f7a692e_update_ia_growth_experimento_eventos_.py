"""update_ia_growth_experimento_eventos_tracking

Revision ID: 89f49f7a692e
Revises: 0f302ce22c97
Create Date: 2026-05-05 00:22:52.867126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89f49f7a692e'
down_revision: Union[str, Sequence[str], None] = '0f302ce22c97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('ia_growth_experimento_eventos', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.add_column('ia_growth_experimento_eventos', sa.Column('usuario_id', sa.Uuid(), nullable=True))
    
    # Preenche tenant_id básico se necessário (opcional se a base estiver vazia)
    # op.execute("UPDATE ia_growth_experimento_eventos SET tenant_id = '...' WHERE tenant_id IS NULL")
    
    # op.alter_column('ia_growth_experimento_eventos', 'tenant_id', nullable=False)
    
    op.create_foreign_key('fk_ia_growth_exp_eventos_tenant', 'ia_growth_experimento_eventos', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_ia_growth_exp_eventos_tenant', 'ia_growth_experimento_eventos', ['tenant_id', 'created_at'])
    op.create_index('ix_ia_growth_exp_eventos_user', 'ia_growth_experimento_eventos', ['usuario_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_ia_growth_exp_eventos_user', table_name='ia_growth_experimento_eventos')
    op.drop_index('ix_ia_growth_exp_eventos_tenant', table_name='ia_growth_experimento_eventos')
    op.drop_constraint('fk_ia_growth_exp_eventos_tenant', 'ia_growth_experimento_eventos', type_='foreignkey')
    op.drop_column('ia_growth_experimento_eventos', 'usuario_id')
    op.drop_column('ia_growth_experimento_eventos', 'tenant_id')
