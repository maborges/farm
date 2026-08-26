"""merge_heads

Revision ID: 86940627be53
Revises: 24e6a080f3b3, a1b2c3d4e5f7, step3_fix_prescricoes_vra
Create Date: 2026-04-06 03:07:11.712206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86940627be53'
# The former parents were descendants through the 8c2e891d6ba9 branch,
# creating a cycle in Alembic's revision graph.  This merge is a historical
# root for the legacy branch; the schema operations remain unchanged.
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
