"""Fase 3 do PLANO-OPERACIONAL-01: produto comercial escolhido por item de plano.

Cria `planos_operacionais_tarefas_insumos` — ponte entre a necessidade técnica
(`safra_tarefa_necessidades`, Fase 2) e o produto real do catálogo, com snapshot
de disponibilidade (lido de `estoque_saldos`) e custo (lido de `Produto.preco_medio`,
sinalizando CUSTO_INCOMPLETO quando não há preço confiável). Somente simulação
nesta fase: nenhuma reserva de estoque é criada (isso é a Fase 4, que estende
`ReservaEstoque` já existente).

Revision ID: 20260726c_plano_op_tarefa_insumo
Revises: 20260726b_tarefa_necessidade_grupo
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260726c_plano_op_tarefa_insumo"
down_revision = "20260726b_tarefa_necessidade_grupo"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "planos_operacionais_tarefas_insumos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plano_operacional_tarefa_id", UUID(as_uuid=True), sa.ForeignKey("planos_operacionais_tarefas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_tarefa_necessidade_id", UUID(as_uuid=True), sa.ForeignKey("safra_tarefa_necessidades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("produto_id", UUID(as_uuid=True), sa.ForeignKey("cadastros_produtos.id"), nullable=False),
        sa.Column("deposito_id", UUID(as_uuid=True), sa.ForeignKey("estoque_depositos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dose_planejada", sa.Numeric(12, 4), nullable=True),
        sa.Column("unidade_dose", sa.String(20), nullable=False),
        sa.Column("quantidade_planejada", sa.Numeric(14, 2), nullable=False),
        sa.Column("quantidade_disponivel_snapshot", sa.Numeric(14, 2), nullable=True),
        sa.Column("quantidade_reservada", sa.Numeric(14, 2), nullable=True),
        sa.Column("quantidade_faltante", sa.Numeric(14, 2), nullable=True),
        sa.Column("custo_unitario_snapshot", sa.Numeric(15, 4), nullable=True),
        sa.Column("custo_total_estimado", sa.Numeric(15, 2), nullable=True),
        sa.Column("fonte_custo", sa.String(30), nullable=True),
        sa.Column("substitui_item_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_foreign_key(
        "fk_plano_op_tarefa_insumos_substitui_item",
        "planos_operacionais_tarefas_insumos",
        "planos_operacionais_tarefas_insumos",
        ["substitui_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_plano_op_tarefa_insumos_tenant_id", "planos_operacionais_tarefas_insumos", ["tenant_id"])
    op.create_index("ix_plano_op_tarefa_insumos_produto_id", "planos_operacionais_tarefas_insumos", ["produto_id"])
    op.create_index(
        "ix_plano_op_tarefa_insumos_tenant_item",
        "planos_operacionais_tarefas_insumos",
        ["tenant_id", "plano_operacional_tarefa_id"],
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_plano_op_tarefa_insumos_tenant_item", table_name="planos_operacionais_tarefas_insumos")
    op.drop_index("ix_plano_op_tarefa_insumos_produto_id", table_name="planos_operacionais_tarefas_insumos")
    op.drop_index("ix_plano_op_tarefa_insumos_tenant_id", table_name="planos_operacionais_tarefas_insumos")
    op.drop_constraint(
        "fk_plano_op_tarefa_insumos_substitui_item",
        "planos_operacionais_tarefas_insumos",
        type_="foreignkey",
    )
    op.drop_table("planos_operacionais_tarefas_insumos")

    op.execute("COMMIT")
