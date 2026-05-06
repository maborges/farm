"""stepGrowth12_ia_growth_user_profile

Revision ID: 0f302ce22c97
Revises: 3d5c5fb9ffa2
Create Date: 2026-05-05 00:19:31.026886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f302ce22c97'
down_revision: Union[str, Sequence[str], None] = '3d5c5fb9ffa2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ia_growth_user_profiles',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('perfil', sa.String(length=40), nullable=False),
        sa.Column('score', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('ix_ia_growth_user_perfil', 'ia_growth_user_profiles', ['perfil'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_ia_growth_user_perfil', table_name='ia_growth_user_profiles')
    op.drop_table('ia_growth_user_profiles')
