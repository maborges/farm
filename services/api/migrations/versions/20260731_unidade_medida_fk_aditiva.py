"""Adiciona unidade_medida_id (FK nullable, aditiva) em 3 tabelas com unidade string livre

Revision ID: 20260731_uom_fk
Revises: 9e4cf920a5b1
Create Date: 2026-07-31

Mudança puramente aditiva: mantém as colunas string antigas (`unidade` /
`unidade_referencia`) intactas e adiciona `unidade_medida_id` como FK
nullable para `unidades_medida.id`, seguindo o mesmo padrão de
`insumos_operacao.unidade_medida_id` (step17_operacoes_execucoes /
operacoes/models.py) e `cenarios` (ondelete="SET NULL", sem backfill).

Nenhum dado existente é alterado — registros antigos ficam com
unidade_medida_id = NULL até serem migrados manualmente/por feature futura.

Tabelas afetadas:
  - agricola_orcamento_itens (ItemOrcamentoSafra.unidade_medida_id)
  - operation_template_items (OperationTemplateItem.unidade_medida_id)
  - safra_tarefa_necessidades (SafraTarefaNecessidade.unidade_medida_id)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_uom_fk"
down_revision: Union[str, Sequence[str], None] = "9e4cf920a5b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agricola_orcamento_itens",
        sa.Column("unidade_medida_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_agricola_orcamento_itens_unidade_medida_id",
        "agricola_orcamento_itens",
        "unidades_medida",
        ["unidade_medida_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "operation_template_items",
        sa.Column("unidade_medida_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_operation_template_items_unidade_medida_id",
        "operation_template_items",
        "unidades_medida",
        ["unidade_medida_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "safra_tarefa_necessidades",
        sa.Column("unidade_medida_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_safra_tarefa_necessidades_unidade_medida_id",
        "safra_tarefa_necessidades",
        "unidades_medida",
        ["unidade_medida_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_safra_tarefa_necessidades_unidade_medida_id",
        "safra_tarefa_necessidades",
        type_="foreignkey",
    )
    op.drop_column("safra_tarefa_necessidades", "unidade_medida_id")

    op.drop_constraint(
        "fk_operation_template_items_unidade_medida_id",
        "operation_template_items",
        type_="foreignkey",
    )
    op.drop_column("operation_template_items", "unidade_medida_id")

    op.drop_constraint(
        "fk_agricola_orcamento_itens_unidade_medida_id",
        "agricola_orcamento_itens",
        type_="foreignkey",
    )
    op.drop_column("agricola_orcamento_itens", "unidade_medida_id")
