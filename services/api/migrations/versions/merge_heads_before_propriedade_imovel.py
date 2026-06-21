"""merge heads before propriedade_imovel

Revision ID: merge_heads_before_propriedade_imovel
Revises: b1c2d3e4f5a7, c3d4e5f6a7b8, ff59b3b71a2d
Create Date: 2026-06-21 00:00:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "merge_heads_before_propriedade_imovel"
down_revision: Union[str, Sequence[str], None] = (
    "b1c2d3e4f5a7",
    "c3d4e5f6a7b8",
    "ff59b3b71a2d",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
