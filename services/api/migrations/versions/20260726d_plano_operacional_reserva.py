"""Fase 4 do PLANO-OPERACIONAL-01: vínculo com reserva real de estoque.

Adiciona `reserva_estoque_id` em `planos_operacionais_tarefas_insumos`, apontando
para `estoque_reservas` (ReservaEstoque) — tabela e serviço de reserva JÁ
EXISTENTES (operacional/models/estoque.py, EstoqueService.criar_reserva), que
já suportam `referencia_tipo`/`referencia_id` genéricos o suficiente para não
precisar de nenhuma mudança na tabela `estoque_reservas` em si. Reserva real só
é criada quando o usuário aprova/reserva um item de plano (fora de RASCUNHO/
simulação); planos em RASCUNHO continuam sem qualquer efeito no saldo.

Revision ID: 20260726d_plano_op_reserva
Revises: 20260726c_plano_op_tarefa_insumo
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260726d_plano_op_reserva"
down_revision = "20260726c_plano_op_tarefa_insumo"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "planos_operacionais_tarefas_insumos",
        sa.Column("reserva_estoque_id", UUID(as_uuid=True), sa.ForeignKey("estoque_reservas.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index(
        "ix_plano_op_tarefa_insumos_reserva",
        "planos_operacionais_tarefas_insumos",
        ["reserva_estoque_id"],
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_plano_op_tarefa_insumos_reserva", table_name="planos_operacionais_tarefas_insumos")
    op.drop_column("planos_operacionais_tarefas_insumos", "reserva_estoque_id")
    op.execute("COMMIT")
