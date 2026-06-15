"""add_qualidade_fields_to_produto_colhido

Revision ID: c0f8b3a1d2e4
Revises: 24ef7c115ab5
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c0f8b3a1d2e4"
down_revision: Union[str, Sequence[str], None] = "24ef7c115ab5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("agricola_produtos_colhidos", schema=None) as batch_op:
        batch_op.add_column(sa.Column("qualidade_laudo_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("qualidade_status", sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column(
                "peso_desconto_qualidade_kg",
                sa.Numeric(precision=14, scale=3),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("peso_liquido_comercial_kg", sa.Numeric(precision=14, scale=3), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_agricola_produtos_colhidos_qualidade_laudo_id"),
            ["qualidade_laudo_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "agricola_produtos_colhidos_qualidade_laudo_id_fkey",
            "operacional_qualidade_laudos",
            ["qualidade_laudo_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("agricola_produtos_colhidos", schema=None) as batch_op:
        batch_op.drop_constraint("agricola_produtos_colhidos_qualidade_laudo_id_fkey", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_agricola_produtos_colhidos_qualidade_laudo_id"))
        batch_op.drop_column("peso_liquido_comercial_kg")
        batch_op.drop_column("peso_desconto_qualidade_kg")
        batch_op.drop_column("qualidade_status")
        batch_op.drop_column("qualidade_laudo_id")
