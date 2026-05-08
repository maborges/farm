"""merge frota and growth heads

Revision ID: 20260507_merge_frota_growth
Revises: 20260507_frota_jornadas, 841554925c14, stepGrowth25
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260507_merge_frota_growth"
down_revision: Union[str, Sequence[str], None] = (
    "20260507_frota_jornadas",
    "841554925c14",
    "stepGrowth25",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
