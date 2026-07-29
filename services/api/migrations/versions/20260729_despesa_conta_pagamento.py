"""Registra a conta bancária de origem na baixa de despesas.

Revision ID: 20260729_despesa_conta_pagamento
Revises: 20260728_plano_op_maquinario
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID


revision = "20260729_despesa_conta_pagamento"
down_revision = "20260728_plano_op_maquinario"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("fin_despesas", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("conta_bancaria_pagamento_id", UUID(as_uuid=True), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_fin_despesas_conta_bancaria_pagamento",
            "fin_contas_bancarias",
            ["conta_bancaria_pagamento_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_fin_despesas_conta_bancaria_pagamento_id",
            ["conta_bancaria_pagamento_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("fin_despesas", schema=None) as batch_op:
        batch_op.drop_index("ix_fin_despesas_conta_bancaria_pagamento_id")
        batch_op.drop_constraint("fk_fin_despesas_conta_bancaria_pagamento", type_="foreignkey")
        batch_op.drop_column("conta_bancaria_pagamento_id")
