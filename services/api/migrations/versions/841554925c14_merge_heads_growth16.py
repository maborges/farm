"""merge heads growth16

Revision ID: 841554925c14
Revises: 20260505_produtos_global, 7a1c2f9d4e31, stepGrowth16
Create Date: 2026-05-07 00:37:51.255951

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '841554925c14'
down_revision: Union[str, Sequence[str], None] = ('20260505_produtos_global', '7a1c2f9d4e31', 'stepGrowth16')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
