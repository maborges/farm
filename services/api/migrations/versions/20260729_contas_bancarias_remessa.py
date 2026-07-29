"""Adiciona configuração de homologação para remessas bancárias.

Revision ID: 20260729_contas_bancarias_remessa
Revises: 20260729_despesa_conta_pagamento
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260729_contas_bancarias_remessa"
down_revision = "20260729_despesa_conta_pagamento"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("fin_contas_bancarias", schema=None) as batch_op:
        batch_op.add_column(sa.Column("convenio_pagamentos", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("layout_remessa", sa.String(length=20), nullable=True))
        batch_op.add_column(
            sa.Column("homologada_para_remessa", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table("fin_contas_bancarias", schema=None) as batch_op:
        batch_op.drop_column("homologada_para_remessa")
        batch_op.drop_column("layout_remessa")
        batch_op.drop_column("convenio_pagamentos")
