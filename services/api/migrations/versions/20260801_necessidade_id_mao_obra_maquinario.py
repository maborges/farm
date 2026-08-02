"""Adiciona safra_tarefa_necessidade_id (FK nullable, aditiva) em mão de obra e maquinário do plano

Revision ID: 20260801_plano_nec_fk
Revises: 20260731_uom_iso80000
Create Date: 2026-08-01

Mudança puramente aditiva, mesmo padrão de
`planos_operacionais_tarefas_insumos.safra_tarefa_necessidade_id`: rastreia
de qual necessidade técnica (categoria MAQUINARIO/MAO_DE_OBRA/SERVICO do
template) o registro de mão de obra/maquinário do plano foi gerado, quando
criado via aplicação em lote — sem isso não dá pra saber quais necessidades
já foram atendidas.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_plano_nec_fk"
down_revision: Union[str, Sequence[str], None] = "20260731_uom_iso80000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "planos_operacionais_tarefas_mao_obra",
        sa.Column("safra_tarefa_necessidade_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_plano_mao_obra_necessidade_id",
        "planos_operacionais_tarefas_mao_obra",
        "safra_tarefa_necessidades",
        ["safra_tarefa_necessidade_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_plano_mao_obra_necessidade_id",
        "planos_operacionais_tarefas_mao_obra",
        ["safra_tarefa_necessidade_id"],
    )

    op.add_column(
        "planos_operacionais_tarefas_maquinario",
        sa.Column("safra_tarefa_necessidade_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_plano_maquinario_necessidade_id",
        "planos_operacionais_tarefas_maquinario",
        "safra_tarefa_necessidades",
        ["safra_tarefa_necessidade_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_plano_maquinario_necessidade_id",
        "planos_operacionais_tarefas_maquinario",
        ["safra_tarefa_necessidade_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_plano_maquinario_necessidade_id", table_name="planos_operacionais_tarefas_maquinario")
    op.drop_constraint("fk_plano_maquinario_necessidade_id", "planos_operacionais_tarefas_maquinario", type_="foreignkey")
    op.drop_column("planos_operacionais_tarefas_maquinario", "safra_tarefa_necessidade_id")

    op.drop_index("ix_plano_mao_obra_necessidade_id", table_name="planos_operacionais_tarefas_mao_obra")
    op.drop_constraint("fk_plano_mao_obra_necessidade_id", "planos_operacionais_tarefas_mao_obra", type_="foreignkey")
    op.drop_column("planos_operacionais_tarefas_mao_obra", "safra_tarefa_necessidade_id")
