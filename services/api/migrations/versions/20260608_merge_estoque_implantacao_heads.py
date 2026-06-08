"""merge estoque implantacao heads

Revision ID: 20260608_merge_estoque_implantacao_heads
Revises: 20260608_estoque_implantacao_confirmacao, 2325278cb390
Create Date: 2026-06-08
"""

from alembic import op


revision = "20260608_merge_estoque_implantacao_heads"
down_revision = ("20260608_estoque_implantacao_confirmacao", "2325278cb390")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
