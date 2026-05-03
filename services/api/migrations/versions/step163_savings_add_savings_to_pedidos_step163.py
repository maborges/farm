"""add_savings_to_pedidos_step163

Revision ID: step163_savings
Revises: b3e0c50368da
Create Date: 2026-05-03 15:24:17.919511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'step163_savings'
down_revision: Union[str, Sequence[str], None] = 'b3e0c50368da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('compras_pedidos', sa.Column('economia_absoluta', sa.Float(), nullable=True, server_default='0'))
    op.add_column('compras_pedidos', sa.Column('economia_percentual', sa.Float(), nullable=True, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('compras_pedidos', 'economia_percentual')
    op.drop_column('compras_pedidos', 'economia_absoluta')
