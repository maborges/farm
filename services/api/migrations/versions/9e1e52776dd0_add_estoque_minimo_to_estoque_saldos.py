"""add estoque_minimo to estoque_saldos

Revision ID: 9e1e52776dd0
Revises: step43_lancamentos_origem
Create Date: 2026-05-03 00:57:58.544569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e1e52776dd0'
down_revision: Union[str, Sequence[str], None] = 'step43_lancamentos_origem'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('estoque_saldos', sa.Column('estoque_minimo', sa.Numeric(precision=18, scale=6), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('estoque_saldos', 'estoque_minimo')
