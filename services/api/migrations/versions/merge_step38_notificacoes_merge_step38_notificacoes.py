"""merge_step38_notificacoes

Revision ID: merge_step38_notificacoes
Revises: step38_ia_checkout, 6a63047d1156
Create Date: 2026-05-02 15:29:25.217156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_step38_notificacoes'
down_revision: Union[str, Sequence[str], None] = ('step38_ia_checkout', '6a63047d1156')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
