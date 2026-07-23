"""compras: permite múltiplos itens por solicitação/cotação/pedido

Cria compras_solicitacoes_itens e compras_cotacoes_itens; adiciona colunas
faltantes em compras_itens_pedido; torna deprecated (nullable) os campos
escalares de item nos cabeçalhos (compras_solicitacoes, compras_cotacoes,
compras_pedidos); faz backfill dos registros existentes criando 1 linha de
item por cabeçalho, preservando os dados atuais.

Revision ID: 20260722h_compras_multi_item
Revises: 20260722g_sequenciais
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722h_compras_multi_item"
down_revision = "20260722g_sequenciais"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # 1. Novas tabelas de item
    op.create_table(
        "compras_solicitacoes_itens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("solicitacao_id", sa.Uuid(as_uuid=True), sa.ForeignKey("compras_solicitacoes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("produto_id", sa.Uuid(as_uuid=True), sa.ForeignKey("cadastros_produtos.id"), nullable=False, index=True),
        sa.Column("deposito_id", sa.Uuid(as_uuid=True), sa.ForeignKey("estoque_depositos.id"), nullable=False, index=True),
        sa.Column("quantidade_solicitada", sa.Float(), nullable=False),
        sa.Column("unidade", sa.String(20), nullable=False),
    )

    op.create_table(
        "compras_cotacoes_itens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("cotacao_id", sa.Uuid(as_uuid=True), sa.ForeignKey("compras_cotacoes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("solicitacao_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("compras_solicitacoes_itens.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("produto_id", sa.Uuid(as_uuid=True), sa.ForeignKey("cadastros_produtos.id"), nullable=False, index=True),
        sa.Column("quantidade", sa.Float(), nullable=False),
        sa.Column("valor_unitario", sa.Float(), nullable=False),
        sa.Column("valor_total", sa.Float(), nullable=False),
    )

    # 2. compras_itens_pedido ganha colunas para virar a linha de item "de verdade"
    op.add_column("compras_itens_pedido", sa.Column("deposito_id", sa.Uuid(as_uuid=True), sa.ForeignKey("estoque_depositos.id"), nullable=True))
    op.add_column("compras_itens_pedido", sa.Column("unidade", sa.String(20), nullable=False, server_default="UN"))
    op.add_column("compras_itens_pedido", sa.Column("valor_total", sa.Float(), nullable=False, server_default="0"))

    # 3. Torna nullable os campos escalares de item nos cabeçalhos (deprecated)
    op.alter_column("compras_solicitacoes", "produto_id", nullable=True)
    op.alter_column("compras_solicitacoes", "deposito_id", nullable=True)
    op.alter_column("compras_solicitacoes", "quantidade_solicitada", nullable=True)
    op.alter_column("compras_solicitacoes", "unidade", nullable=True)

    op.alter_column("compras_cotacoes", "valor_unitario", nullable=True)
    # valor_total já era NOT NULL e permanece populado (agora como rollup dos itens
    # para cotações novas; para as existentes, o valor escalar antigo já é o total correto).

    op.alter_column("compras_pedidos", "item_id", nullable=True)
    op.alter_column("compras_pedidos", "deposito_id", nullable=True)
    op.alter_column("compras_pedidos", "quantidade", nullable=True)
    op.alter_column("compras_pedidos", "unidade", nullable=True)
    op.alter_column("compras_pedidos", "valor_unitario", nullable=True)

    # 4. Backfill: 1 linha de item por cabeçalho existente, a partir dos dados escalares.
    bind.execute(sa.text("""
        INSERT INTO compras_solicitacoes_itens (id, solicitacao_id, produto_id, deposito_id, quantidade_solicitada, unidade)
        SELECT gen_random_uuid(), id, produto_id, deposito_id, quantidade_solicitada, unidade
        FROM compras_solicitacoes
        WHERE produto_id IS NOT NULL AND deposito_id IS NOT NULL
    """))

    bind.execute(sa.text("""
        INSERT INTO compras_cotacoes_itens (id, cotacao_id, solicitacao_item_id, produto_id, quantidade, valor_unitario, valor_total)
        SELECT gen_random_uuid(), c.id, si.id, si.produto_id, si.quantidade_solicitada, c.valor_unitario, c.valor_total
        FROM compras_cotacoes c
        JOIN compras_solicitacoes_itens si ON si.solicitacao_id = c.solicitacao_id
        WHERE c.valor_unitario IS NOT NULL
    """))

    bind.execute(sa.text("""
        UPDATE compras_itens_pedido ip
        SET deposito_id = p.deposito_id,
            unidade = COALESCE(p.unidade, 'UN'),
            valor_total = ip.quantidade_solicitada * COALESCE(ip.preco_estimado_unitario, 0)
        FROM compras_pedidos p
        WHERE ip.pedido_id = p.id
    """))

    # Pedidos sem nenhuma linha em compras_itens_pedido (fluxo legado que nunca
    # chamou _get_or_create_item_pedido_principal): cria a linha a partir do cabeçalho.
    bind.execute(sa.text("""
        INSERT INTO compras_itens_pedido (id, pedido_id, produto_id, deposito_id, unidade, quantidade_solicitada, preco_estimado_unitario, valor_total, quantidade_recebida, preco_real_unitario, status_item)
        SELECT gen_random_uuid(), p.id, p.item_id, p.deposito_id, COALESCE(p.unidade, 'UN'), p.quantidade, p.valor_unitario, p.valor_total, 0, NULL, 'PENDENTE'
        FROM compras_pedidos p
        WHERE p.item_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM compras_itens_pedido ip WHERE ip.pedido_id = p.id)
    """))

    op.execute("COMMIT")


def downgrade():
    op.drop_column("compras_itens_pedido", "valor_total")
    op.drop_column("compras_itens_pedido", "unidade")
    op.drop_column("compras_itens_pedido", "deposito_id")

    op.drop_table("compras_cotacoes_itens")
    op.drop_table("compras_solicitacoes_itens")

    op.execute("COMMIT")
