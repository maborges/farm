"""add navigation_mode to usuarios

Revision ID: 9e4cf920a5b1
Revises: 67b25594e50f
Create Date: 2026-07-30 21:08:16.537082

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9e4cf920a5b1'
down_revision: Union[str, Sequence[str], None] = '67b25594e50f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('usuarios', sa.Column('navigation_mode', sa.String(length=20), server_default='SIDEBAR', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('usuarios', 'navigation_mode')
