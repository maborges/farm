"""corrige numero de pedido/cotação para único por tenant, não globalmente

O índice único criado em 20260722g cobria só a coluna `numero`, então
tenants diferentes colidiam ao gerar o mesmo número (ex: dois tenants
criando seu primeiro pedido, ambos "PED-2026-000001"). Troca por
UNIQUE(tenant_id, numero).

Revision ID: 20260722i_numero_unico_tenant
Revises: 20260722h_compras_multi_item
Create Date: 2026-07-22
"""
from alembic import op

revision = "20260722i_numero_unico_tenant"
down_revision = "20260722h_compras_multi_item"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_compras_cotacoes_numero", table_name="compras_cotacoes")
    op.create_index("ix_compras_cotacoes_numero", "compras_cotacoes", ["numero"], unique=False)
    op.create_unique_constraint(
        "uq_compras_cotacoes_tenant_numero", "compras_cotacoes", ["tenant_id", "numero"]
    )

    op.drop_index("ix_compras_pedidos_numero", table_name="compras_pedidos")
    op.create_index("ix_compras_pedidos_numero", "compras_pedidos", ["numero"], unique=False)
    op.create_unique_constraint(
        "uq_compras_pedidos_tenant_numero", "compras_pedidos", ["tenant_id", "numero"]
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_constraint("uq_compras_pedidos_tenant_numero", "compras_pedidos", type_="unique")
    op.drop_index("ix_compras_pedidos_numero", table_name="compras_pedidos")
    op.create_index("ix_compras_pedidos_numero", "compras_pedidos", ["numero"], unique=True)

    op.drop_constraint("uq_compras_cotacoes_tenant_numero", "compras_cotacoes", type_="unique")
    op.drop_index("ix_compras_cotacoes_numero", table_name="compras_cotacoes")
    op.create_index("ix_compras_cotacoes_numero", "compras_cotacoes", ["numero"], unique=True)

    op.execute("COMMIT")
