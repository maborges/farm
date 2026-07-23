"""compras_pedidos: saneamento de dados legados — backfill de
usuario_solicitante_id (a partir da solicitação de origem) e valor_unitario
(a partir do item único, quando aplicável), para registros já existentes
que ficaram NULL/dessincronizados antes da correção na camada de serviço.

Revision ID: 20260723d_backfill_ped
Revises: 20260723c_pedido_adto_zero
Create Date: 2026-07-23
"""
from alembic import op

revision = "20260723d_backfill_ped"
down_revision = "20260723c_pedido_adto_zero"
branch_labels = None
depends_on = None


def upgrade():
    # 1) usuario_solicitante_id: copia da solicitação de origem quando o
    #    pedido não tem (registros criados antes da correção do serviço).
    op.execute(
        """
        UPDATE compras_pedidos AS p
        SET usuario_solicitante_id = s.solicitante_id
        FROM compras_solicitacoes AS s
        WHERE p.solicitacao_id = s.id
          AND p.tenant_id = s.tenant_id
          AND p.usuario_solicitante_id IS NULL
          AND s.solicitante_id IS NOT NULL
        """
    )

    # 2) valor_unitario: sincroniza com o preço do item único do pedido
    #    (campo legado — só faz sentido quando há exatamente 1 item).
    op.execute(
        """
        UPDATE compras_pedidos AS p
        SET valor_unitario = i.preco_estimado_unitario
        FROM compras_itens_pedido AS i
        WHERE i.pedido_id = p.id
          AND (
              SELECT COUNT(*) FROM compras_itens_pedido ii WHERE ii.pedido_id = p.id
          ) = 1
          AND p.valor_unitario IS DISTINCT FROM i.preco_estimado_unitario
        """
    )

    # 3) valor_unitario: zera (NULL) para pedidos multi-item que ficaram com
    #    um valor legado de quando tinham 1 item só (ex.: itens adicionados
    #    depois via ajuste manual).
    op.execute(
        """
        UPDATE compras_pedidos AS p
        SET valor_unitario = NULL
        WHERE p.valor_unitario IS NOT NULL
          AND (
              SELECT COUNT(*) FROM compras_itens_pedido ii WHERE ii.pedido_id = p.id
          ) > 1
        """
    )
    op.execute("COMMIT")


def downgrade():
    # Backfill é apenas de dados — não há downgrade estrutural aplicável.
    pass
