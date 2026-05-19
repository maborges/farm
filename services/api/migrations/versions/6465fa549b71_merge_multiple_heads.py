"""Merge multiple heads

Revision ID: 6465fa549b71
Revises: 20260508_recomendado_ia, 20260518_frota_alocacoes
Create Date: 2026-05-18 08:12:36.021828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6465fa549b71'
down_revision: Union[str, Sequence[str], None] = ('20260508_recomendado_ia', '20260518_frota_alocacoes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
