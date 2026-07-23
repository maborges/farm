"""cria tabela core_sequenciais e coluna numero em cotacoes/pedidos

Revision ID: 20260722g_sequenciais
Revises: 20260722f_cotacao_fornecedor
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722g_sequenciais"
down_revision = "20260722f_cotacao_fornecedor"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "core_sequenciais",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("entidade", sa.String(50), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=True),
        sa.Column("ultimo_numero", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "entidade", "ano", name="uq_core_sequenciais_tenant_entidade_ano"),
    )

    op.add_column("compras_cotacoes", sa.Column("numero", sa.String(30), nullable=True))
    op.create_index("ix_compras_cotacoes_numero", "compras_cotacoes", ["numero"], unique=True)

    op.add_column("compras_pedidos", sa.Column("numero", sa.String(30), nullable=True))
    op.create_index("ix_compras_pedidos_numero", "compras_pedidos", ["numero"], unique=True)

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_compras_pedidos_numero", table_name="compras_pedidos")
    op.drop_column("compras_pedidos", "numero")

    op.drop_index("ix_compras_cotacoes_numero", table_name="compras_cotacoes")
    op.drop_column("compras_cotacoes", "numero")

    op.drop_table("core_sequenciais")

    op.execute("COMMIT")
