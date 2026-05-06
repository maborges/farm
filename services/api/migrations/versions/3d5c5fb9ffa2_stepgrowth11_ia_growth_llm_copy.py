"""stepGrowth11_ia_growth_llm_copy

Revision ID: 3d5c5fb9ffa2
Revises: stepGrowth10
Create Date: 2026-05-05 00:14:12.161166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d5c5fb9ffa2'
down_revision: Union[str, Sequence[str], None] = 'stepGrowth10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Tabela de Cache de Copy LLM
    op.create_table(
        'ia_growth_copy_cache',
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('contexto', sa.String(length=40), nullable=False),
        sa.Column('perfil_hash', sa.String(length=64), nullable=False),
        sa.Column('cta', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tenant_id', 'contexto', 'perfil_hash')
    )

    # 2. Rastreamento de proveniência nas variantes
    op.add_column('ia_growth_experimento_variantes', sa.Column('origem_copy', sa.String(length=20), nullable=False, server_default='HEURISTICA'))
    
    # 3. Rastreamento de proveniência nos eventos
    op.add_column('ia_growth_experimento_eventos', sa.Column('origem_copy', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ia_growth_experimento_eventos', 'origem_copy')
    op.drop_column('ia_growth_experimento_variantes', 'origem_copy')
    op.drop_table('ia_growth_copy_cache')
