"""estoque contagens (OPERATIONS-GAP-01 §21.30)

Revision ID: 20260815_estoque_contagens
Revises: 20260815_equipamento_categoria_patrimonial
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_estoque_contagens"
down_revision = "20260815_equipamento_categoria_patrimonial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "estoque_contagens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deposito_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estoque_depositos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ABERTA"),
        sa.Column("aberta_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("aberta_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("concluida_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
    )
    op.create_index("ix_estoque_contagens_tenant_id", "estoque_contagens", ["tenant_id"])
    op.create_index("ix_estoque_contagens_deposito_id", "estoque_contagens", ["deposito_id"])
    op.create_index(
        "ix_estoque_contagens_tenant_deposito_status", "estoque_contagens",
        ["tenant_id", "deposito_id", "status"],
    )

    op.create_table(
        "estoque_contagem_itens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contagem_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estoque_contagens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("produto_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantidade_sistema", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantidade_contada", sa.Numeric(18, 6), nullable=True),
        sa.Column("contado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("movimento_ajuste_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estoque_movimentos.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_estoque_contagem_itens_tenant_id", "estoque_contagem_itens", ["tenant_id"])
    op.create_index("ix_estoque_contagem_itens_contagem_id", "estoque_contagem_itens", ["contagem_id"])
    op.create_index("ix_estoque_contagem_itens_produto_id", "estoque_contagem_itens", ["produto_id"])
    op.create_index(
        "ix_estoque_contagem_itens_tenant_contagem", "estoque_contagem_itens",
        ["tenant_id", "contagem_id"],
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_table("estoque_contagem_itens")
    op.drop_table("estoque_contagens")
    op.execute("COMMIT")
