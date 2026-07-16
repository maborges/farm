"""merge_heads_01H2

Revision ID: 5cee1dab62fb
Revises: 6e6fda192744, step28_area_total_calculada_unidades_produtivas
Create Date: 2026-07-16 10:33:38.525819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5cee1dab62fb'
down_revision: Union[str, Sequence[str], None] = ('6e6fda192744', 'step28_area_total_calculada_unidades_produtivas')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
