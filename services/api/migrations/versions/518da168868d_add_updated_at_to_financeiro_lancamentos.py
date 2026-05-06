"""add updated_at to financeiro_lancamentos

Revision ID: 518da168868d
Revises: step180_merge_heads
Create Date: 2026-05-03 21:13:20.393434

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '518da168868d'
down_revision: Union[str, Sequence[str], None] = 'step180_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona a coluna updated_at com valor default para registros existentes
    op.add_column('financeiro_lancamentos', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    op.drop_column('financeiro_lancamentos', 'updated_at')
