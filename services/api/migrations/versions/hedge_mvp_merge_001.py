"""Merge: hedge_mvp_001 + 1b7d1c4f9a22 (qualidade_efetiva)

Revision ID: hedge_mvp_merge_001
Revises: hedge_mvp_001, 1b7d1c4f9a22
Create Date: 2026-06-15
"""
from alembic import op

revision = "hedge_mvp_merge_001"
down_revision = ("hedge_mvp_001", "1b7d1c4f9a22")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge — sem alterações de schema."""
    pass


def downgrade() -> None:
    """Merge — sem alterações de schema."""
    pass
