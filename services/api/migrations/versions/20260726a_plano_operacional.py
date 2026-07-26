"""Fase 1 do PLANO-OPERACIONAL-01: cabeçalho e associação de tarefas do
Planejamento Operacional em Lote.

Cria `planos_operacionais` (cabeçalho decisório, cobre N talhões da mesma safra)
e `planos_operacionais_tarefas` (associação com `SafraTarefa`, sempre 1 talhão por
tarefa — o agrupamento é só nesta camada de planejamento, não altera a tarefa).
Sem reserva de estoque, compras ou mão de obra ainda — ver
docs/implementation/reports/PLANO-OPERACIONAL-01-AUDITORIA-CONTRATO-DOMINIO.md.

Revision ID: 20260726a_plano_operacional
Revises: 20260725e_campo_tarefa_vinculo
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260726a_plano_operacional"
down_revision = "20260725e_campo_tarefa_vinculo"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "planos_operacionais",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_id", UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("production_unit_id", UUID(as_uuid=True), sa.ForeignKey("production_units.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("data_inicio_prevista", sa.Date(), nullable=False),
        sa.Column("data_fim_prevista", sa.Date(), nullable=True),
        sa.Column("status", sa.String(25), nullable=False, server_default="RASCUNHO"),
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("criado_por", UUID(as_uuid=True), nullable=True),
        sa.Column("aprovado_por", UUID(as_uuid=True), nullable=True),
        sa.Column("aprovado_em", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_planos_operacionais_tenant_id", "planos_operacionais", ["tenant_id"])
    op.create_index("ix_planos_operacionais_safra_id", "planos_operacionais", ["safra_id"])
    op.create_index("ix_planos_operacionais_status", "planos_operacionais", ["status"])
    op.create_index(
        "ix_planos_operacionais_tenant_safra_status",
        "planos_operacionais",
        ["tenant_id", "safra_id", "status"],
    )

    op.create_table(
        "planos_operacionais_tarefas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plano_operacional_id", UUID(as_uuid=True), sa.ForeignKey("planos_operacionais.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_tarefa_id", UUID(as_uuid=True), sa.ForeignKey("safra_tarefas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status_planejamento", sa.String(25), nullable=False, server_default="NAO_ANALISADA"),
        sa.Column("data_programada", sa.Date(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("ordem_execucao", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("plano_operacional_id", "safra_tarefa_id", name="uq_plano_operacional_tarefa"),
    )
    op.create_index("ix_plano_op_tarefas_tenant_id", "planos_operacionais_tarefas", ["tenant_id"])
    op.create_index("ix_plano_op_tarefas_plano_id", "planos_operacionais_tarefas", ["plano_operacional_id"])
    op.create_index("ix_plano_op_tarefas_safra_tarefa_id", "planos_operacionais_tarefas", ["safra_tarefa_id"])
    op.create_index(
        "ix_plano_op_tarefas_tenant_plano",
        "planos_operacionais_tarefas",
        ["tenant_id", "plano_operacional_id"],
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_plano_op_tarefas_tenant_plano", table_name="planos_operacionais_tarefas")
    op.drop_index("ix_plano_op_tarefas_safra_tarefa_id", table_name="planos_operacionais_tarefas")
    op.drop_index("ix_plano_op_tarefas_plano_id", table_name="planos_operacionais_tarefas")
    op.drop_index("ix_plano_op_tarefas_tenant_id", table_name="planos_operacionais_tarefas")
    op.drop_table("planos_operacionais_tarefas")

    op.drop_index("ix_planos_operacionais_tenant_safra_status", table_name="planos_operacionais")
    op.drop_index("ix_planos_operacionais_status", table_name="planos_operacionais")
    op.drop_index("ix_planos_operacionais_safra_id", table_name="planos_operacionais")
    op.drop_index("ix_planos_operacionais_tenant_id", table_name="planos_operacionais")
    op.drop_table("planos_operacionais")

    op.execute("COMMIT")
