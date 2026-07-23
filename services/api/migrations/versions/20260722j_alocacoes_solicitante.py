"""compras: alocação item×fornecedor (atendimento parcial) + solicitante da solicitação

Cria compras_alocacoes_item (quanto de um item foi alocado a qual cotação de
fornecedor, podendo haver várias linhas por item — atendimento parcial por
N fornecedores). Adiciona compras_solicitacoes.solicitante_id, usado para
restringir a ação de encerrar uma solicitação parcialmente atendida a quem
a criou.

Revision ID: 20260722j_alocacoes_solicitante
Revises: 20260722i_numero_unico_tenant
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722j_alocacoes_solicitante"
down_revision = "20260722i_numero_unico_tenant"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "compras_solicitacoes",
        sa.Column("solicitante_id", sa.Uuid(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
    )

    op.create_table(
        "compras_alocacoes_item",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("solicitacao_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("compras_solicitacoes_itens.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("cotacao_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("compras_cotacoes_itens.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("quantidade_alocada", sa.Float(), nullable=False),
        sa.Column("pedido_id", sa.Uuid(as_uuid=True), sa.ForeignKey("compras_pedidos.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_table("compras_alocacoes_item")
    op.drop_column("compras_solicitacoes", "solicitante_id")
    op.execute("COMMIT")
