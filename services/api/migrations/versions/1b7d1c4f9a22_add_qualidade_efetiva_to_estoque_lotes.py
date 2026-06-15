"""add qualidade efetiva to estoque lotes

Revision ID: 1b7d1c4f9a22
Revises: c0f8b3a1d2e4
Create Date: 2026-06-14 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1b7d1c4f9a22"
down_revision = "c0f8b3a1d2e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("estoque_lotes", sa.Column("qualidade_laudo_id", sa.UUID(), nullable=True))
    op.add_column("estoque_lotes", sa.Column("qualidade_status", sa.String(length=50), nullable=True))
    op.add_column(
        "estoque_lotes",
        sa.Column(
            "peso_desconto_qualidade_kg",
            sa.Numeric(12, 3),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column("estoque_lotes", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_estoque_lotes_qualidade_laudo_id",
        "estoque_lotes",
        "operacional_qualidade_laudos",
        ["qualidade_laudo_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_estoque_lotes_qualidade_laudo_id",
        "estoque_lotes",
        ["qualidade_laudo_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_estoque_lotes_qualidade_laudo_id", table_name="estoque_lotes")
    op.drop_constraint("fk_estoque_lotes_qualidade_laudo_id", "estoque_lotes", type_="foreignkey")
    op.drop_column("estoque_lotes", "metadata_json")
    op.drop_column("estoque_lotes", "peso_desconto_qualidade_kg")
    op.drop_column("estoque_lotes", "qualidade_status")
    op.drop_column("estoque_lotes", "qualidade_laudo_id")
