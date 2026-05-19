"""frota_step04_add_checklist_and_categoria
Revision ID: 20260521_frota_step04
Revises: 20260520_frota_step02
Create Date: 2026-05-21 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260521_frota_step04"
down_revision = "20260520_frota_step02"
branch_labels = None
depends_on = None

_SCHEMA = "farms"


def upgrade() -> None:
    with op.batch_alter_table("frota_planos_manutencao", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("checklist_preventivo", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("categoria", sa.String(length=100), nullable=True))

    with op.batch_alter_table("frota_ordens_servico", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("checklist_aplicado", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("frota_ordens_servico", schema=_SCHEMA) as batch_op:
        batch_op.drop_column("checklist_aplicado")

    with op.batch_alter_table("frota_planos_manutencao", schema=_SCHEMA) as batch_op:
        batch_op.drop_column("categoria")
        batch_op.drop_column("checklist_preventivo")
