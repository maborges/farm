"""Receitas de Aplicação — cadastro reutilizável de produto+dose/ha e mão de
obra padrão, aplicável em lote a várias tarefas de um Planejamento Operacional
(evita lançar insumo/mão de obra um a um por tarefa quando várias tarefas do
mesmo plano usam o mesmo pacote — ex.: mesma pulverização em vários talhões).

Revision ID: 20260727_receitas_aplicacao
Revises: 20260726e_plano_op_mao_obra
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260727_receitas_aplicacao"
down_revision = "20260726e_plano_op_mao_obra"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "receitas_aplicacao",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("tipo_operacao", sa.String(50), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_receitas_aplicacao_tenant_id", "receitas_aplicacao", ["tenant_id"])
    op.create_index("ix_receitas_aplicacao_tenant_nome", "receitas_aplicacao", ["tenant_id", "nome"])

    op.create_table(
        "receitas_aplicacao_insumos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receita_id", UUID(as_uuid=True), sa.ForeignKey("receitas_aplicacao.id", ondelete="CASCADE"), nullable=False),
        sa.Column("produto_id", UUID(as_uuid=True), sa.ForeignKey("cadastros_produtos.id"), nullable=False),
        sa.Column("deposito_id", UUID(as_uuid=True), sa.ForeignKey("estoque_depositos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dose_ha", sa.Numeric(12, 4), nullable=False),
        sa.Column("unidade_dose", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_receitas_aplicacao_insumos_tenant_id", "receitas_aplicacao_insumos", ["tenant_id"])
    op.create_index("ix_receitas_aplicacao_insumos_receita", "receitas_aplicacao_insumos", ["tenant_id", "receita_id"])

    op.create_table(
        "receitas_aplicacao_mao_obra",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receita_id", UUID(as_uuid=True), sa.ForeignKey("receitas_aplicacao.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_servico_id", UUID(as_uuid=True), sa.ForeignKey("cadastros_tipos_servico.id"), nullable=False),
        sa.Column("funcao", sa.String(100), nullable=True),
        sa.Column("quantidade_pessoas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("horas_fixas", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("horas_por_hectare", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_receitas_aplicacao_mao_obra_tenant_id", "receitas_aplicacao_mao_obra", ["tenant_id"])
    op.create_index("ix_receitas_aplicacao_mao_obra_receita", "receitas_aplicacao_mao_obra", ["tenant_id", "receita_id"])

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_receitas_aplicacao_mao_obra_receita", table_name="receitas_aplicacao_mao_obra")
    op.drop_index("ix_receitas_aplicacao_mao_obra_tenant_id", table_name="receitas_aplicacao_mao_obra")
    op.drop_table("receitas_aplicacao_mao_obra")

    op.drop_index("ix_receitas_aplicacao_insumos_receita", table_name="receitas_aplicacao_insumos")
    op.drop_index("ix_receitas_aplicacao_insumos_tenant_id", table_name="receitas_aplicacao_insumos")
    op.drop_table("receitas_aplicacao_insumos")

    op.drop_index("ix_receitas_aplicacao_tenant_nome", table_name="receitas_aplicacao")
    op.drop_index("ix_receitas_aplicacao_tenant_id", table_name="receitas_aplicacao")
    op.drop_table("receitas_aplicacao")

    op.execute("COMMIT")
