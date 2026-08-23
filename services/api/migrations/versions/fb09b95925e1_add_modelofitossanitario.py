"""Add ModeloFitossanitario

Revision ID: fb09b95925e1
Revises: 20260821_previsao_periodos
Create Date: 2026-08-22 00:04:15.635738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb09b95925e1'
down_revision: Union[str, Sequence[str], None] = '20260821_previsao_periodos'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'modelos_fitossanitarios',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('cultura', sa.String(length=100), nullable=False),
        sa.Column('doenca', sa.String(length=150), nullable=False),
        sa.Column('regras_risco', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cultura', 'doenca', name='uq_modelos_fito_cultura_doenca')
    )
    with op.batch_alter_table('modelos_fitossanitarios', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_modelos_fitossanitarios_cultura'), ['cultura'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('modelos_fitossanitarios', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_modelos_fitossanitarios_cultura'))

    op.drop_table('modelos_fitossanitarios')
