"""add_complemento_to_unidade_produtiva

Revision ID: 6e6fda192744
Revises: 8c3e031c97b4
Create Date: 2026-07-13 22:37:20.885646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6e6fda192744'
down_revision: Union[str, Sequence[str], None] = '8c3e031c97b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('unidades_produtivas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('complemento', sa.String(length=100), nullable=True, comment='Complemento do endereço'))

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('unidades_produtivas', schema=None) as batch_op:
        batch_op.drop_column('complemento')

    # ### end Alembic commands ###
