"""Espelha a Fase 6 (mão de obra) do PLANO-OPERACIONAL-01 para maquinário.

Cria `planos_operacionais_tarefas_maquinario`, vinculada a `Equipamento`
(`cadastros_equipamentos`) tanto para a máquina quanto para o implemento —
mesmo cadastro mestre, dois papéis. Custo/hora é capturado via
`SnapshotCustoService(origem_tipo="MAQUINA")`, que já usa
`FrotaCustoService.obter_custo_equipamento` (custo acumulado real / horímetro)
— nenhuma lógica de custo nova, nenhum campo novo em `Equipamento`.

Revision ID: 20260728_plano_op_maquinario
Revises: 20260727_receitas_aplicacao
Create Date: 2026-07-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260728_plano_op_maquinario"
down_revision = "20260727_receitas_aplicacao"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "planos_operacionais_tarefas_maquinario",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "plano_operacional_tarefa_id",
            UUID(as_uuid=True),
            sa.ForeignKey("planos_operacionais_tarefas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "maquina_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cadastros_equipamentos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "implemento_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cadastros_equipamentos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("horas_estimadas", sa.Numeric(10, 2), nullable=True),
        sa.Column("custo_hora_maquina_snapshot", sa.Numeric(15, 4), nullable=True),
        sa.Column("custo_hora_implemento_snapshot", sa.Numeric(15, 4), nullable=True),
        sa.Column("custo_total_estimado", sa.Numeric(15, 2), nullable=True),
        sa.Column("fonte_custo", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index(
        "ix_plano_op_tarefa_maquinario_tenant_id", "planos_operacionais_tarefas_maquinario", ["tenant_id"]
    )
    op.create_index(
        "ix_plano_op_tarefa_maquinario_tenant_item",
        "planos_operacionais_tarefas_maquinario",
        ["tenant_id", "plano_operacional_tarefa_id"],
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_plano_op_tarefa_maquinario_tenant_item", table_name="planos_operacionais_tarefas_maquinario")
    op.drop_index("ix_plano_op_tarefa_maquinario_tenant_id", table_name="planos_operacionais_tarefas_maquinario")
    op.drop_table("planos_operacionais_tarefas_maquinario")
    op.execute("COMMIT")
