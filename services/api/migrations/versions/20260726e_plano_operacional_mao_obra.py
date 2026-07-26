"""Fase 6 do PLANO-OPERACIONAL-01: necessidade de mão de obra por item de plano.

Cria `planos_operacionais_tarefas_mao_obra`, vinculada a `TipoServico`
(catálogo já existente, mesmo padrão de Produto/Equipamento/ColaboradorRH) e
opcionalmente a uma pessoa (`cadastros_pessoas`). Deliberadamente separada de
`OperacaoAgricola.operador_id` (quem efetivamente executa, só existe na OS) —
aqui é só a estimativa de planejamento (equipe ainda pode não estar definida).

Revision ID: 20260726e_plano_op_mao_obra
Revises: 20260726d_plano_op_reserva
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260726e_plano_op_mao_obra"
down_revision = "20260726d_plano_op_reserva"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "planos_operacionais_tarefas_mao_obra",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plano_operacional_tarefa_id", UUID(as_uuid=True), sa.ForeignKey("planos_operacionais_tarefas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_servico_id", UUID(as_uuid=True), sa.ForeignKey("cadastros_tipos_servico.id"), nullable=False),
        sa.Column("pessoa_id", UUID(as_uuid=True), sa.ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("funcao", sa.String(100), nullable=True),
        sa.Column("quantidade_pessoas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("horas_estimadas", sa.Numeric(10, 2), nullable=True),
        sa.Column("custo_hora_snapshot", sa.Numeric(15, 4), nullable=True),
        sa.Column("custo_total_estimado", sa.Numeric(15, 2), nullable=True),
        sa.Column("fonte_custo", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_plano_op_tarefa_mao_obra_tenant_id", "planos_operacionais_tarefas_mao_obra", ["tenant_id"])
    op.create_index(
        "ix_plano_op_tarefa_mao_obra_tenant_item",
        "planos_operacionais_tarefas_mao_obra",
        ["tenant_id", "plano_operacional_tarefa_id"],
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_plano_op_tarefa_mao_obra_tenant_item", table_name="planos_operacionais_tarefas_mao_obra")
    op.drop_index("ix_plano_op_tarefa_mao_obra_tenant_id", table_name="planos_operacionais_tarefas_mao_obra")
    op.drop_table("planos_operacionais_tarefas_mao_obra")
    op.execute("COMMIT")
