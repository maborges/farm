"""Vincula TarefaCampo (campo_tarefas) à origem agrícola (SafraTarefa/OperacaoAgricola).

Fecha o loop planejamento -> campo: quando uma OS (OperacaoAgricola PLANEJADA) é
gerada a partir de uma SafraTarefa aprovada, uma TarefaCampo (origem=PROGRAMADA)
correspondente passa a ser criada para aparecer em "Tarefas de Campo". Essas duas
colunas guardam a origem sem reaproveitar `OperacaoAgricola.tarefa_id` (que já tem
FK própria para safra_tarefas.id e não deve ser confundida com campo_tarefas.id).

Revision ID: 20260725e_campo_tarefa_vinculo
Revises: 20260725d_tipo_servico_catalogo_global
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260725e_campo_tarefa_vinculo"
down_revision = "20260725d_tipo_servico_catalogo_global"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "campo_tarefas",
        sa.Column("safra_tarefa_id", UUID(as_uuid=True), sa.ForeignKey("safra_tarefas.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "campo_tarefas",
        sa.Column("operacao_agricola_id", UUID(as_uuid=True), sa.ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_campo_tarefas_safra_tarefa", "campo_tarefas", ["safra_tarefa_id"])
    op.create_index("ix_campo_tarefas_operacao_agricola", "campo_tarefas", ["operacao_agricola_id"])
    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_campo_tarefas_operacao_agricola", table_name="campo_tarefas")
    op.drop_index("ix_campo_tarefas_safra_tarefa", table_name="campo_tarefas")
    op.drop_column("campo_tarefas", "operacao_agricola_id")
    op.drop_column("campo_tarefas", "safra_tarefa_id")
    op.execute("COMMIT")
