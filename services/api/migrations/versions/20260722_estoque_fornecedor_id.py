"""adiciona fornecedor_id em estoque_movimentos

Revision ID: 20260722_estoque_fornecedor
Revises: 20260718_sankhya_ids
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260722_estoque_fornecedor"
down_revision = "20260718_sankhya_ids"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "estoque_movimentos",
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_estoque_movimentos_fornecedor_id",
        "estoque_movimentos",
        "compras_fornecedores",
        ["fornecedor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_estoque_movimentos_fornecedor_id",
        "estoque_movimentos",
        ["fornecedor_id"],
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_estoque_movimentos_fornecedor_id", table_name="estoque_movimentos")
    op.drop_constraint("fk_estoque_movimentos_fornecedor_id", "estoque_movimentos", type_="foreignkey")
    op.drop_column("estoque_movimentos", "fornecedor_id")
    op.execute("COMMIT")
