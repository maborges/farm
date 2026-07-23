"""compras_pedidos: remove campos legados de item único
(item_id, deposito_id, quantidade, unidade, valor_unitario) — substituídos
por ItemPedidoCompra (compras_itens_pedido, já em uso desde o multi-item).
Remove também observacoes e data_pedido, nunca escritos pela camada de
serviço, e o synonym Python deposito_destino_id (sem coluna própria).

Revision ID: 20260723e_ped_drop_legado
Revises: 20260723d_backfill_ped
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260723e_ped_drop_legado"
down_revision = "20260723d_backfill_ped"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("fk_pedido_item", "compras_pedidos", type_="foreignkey")
    op.drop_constraint("fk_pedido_deposito", "compras_pedidos", type_="foreignkey")
    op.drop_constraint("fk_cp_tenant_deposito", "compras_pedidos", type_="foreignkey")
    op.drop_column("compras_pedidos", "item_id")
    op.drop_column("compras_pedidos", "deposito_id")
    op.drop_column("compras_pedidos", "quantidade")
    op.drop_column("compras_pedidos", "unidade")
    op.drop_column("compras_pedidos", "valor_unitario")
    op.drop_column("compras_pedidos", "observacoes")
    op.drop_column("compras_pedidos", "data_pedido")
    op.execute("COMMIT")


def downgrade():
    op.add_column("compras_pedidos", sa.Column("item_id", sa.Uuid(), nullable=True))
    op.add_column("compras_pedidos", sa.Column("deposito_id", sa.Uuid(), nullable=True))
    op.add_column("compras_pedidos", sa.Column("quantidade", sa.Float(), nullable=True))
    op.add_column("compras_pedidos", sa.Column("unidade", sa.String(20), nullable=True))
    op.add_column("compras_pedidos", sa.Column("valor_unitario", sa.Float(), nullable=True))
    op.add_column("compras_pedidos", sa.Column("observacoes", sa.String(500), nullable=True))
    op.add_column(
        "compras_pedidos",
        sa.Column("data_pedido", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key("fk_pedido_item", "compras_pedidos", "cadastros_produtos", ["item_id"], ["id"])
    op.create_foreign_key("fk_pedido_deposito", "compras_pedidos", "estoque_depositos", ["deposito_id"], ["id"])
    op.create_foreign_key(
        "fk_cp_tenant_deposito",
        "compras_pedidos",
        "estoque_depositos",
        ["tenant_id", "deposito_id"],
        ["tenant_id", "id"],
    )
    op.execute("COMMIT")
