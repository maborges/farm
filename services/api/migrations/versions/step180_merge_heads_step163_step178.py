"""step180: merge heads step163_savings e step178

Revision ID: step180_merge_heads
Revises: step163_savings, step178
Create Date: 2026-05-03
"""
from typing import Sequence, Union


revision: str = "step180_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("step163_savings", "step178")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge revision sem alterações de schema."""
    pass


def downgrade() -> None:
    """Desfaz merge lógico sem alterações de schema."""
    pass
