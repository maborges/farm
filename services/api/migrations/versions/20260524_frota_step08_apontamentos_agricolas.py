"""frota_step08_apontamentos_agricolas

Revision ID: 20260524_frota_step08
Revises: 20260523_frota_step07
Create Date: 2026-05-24 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260524_frota_step08"
down_revision = "20260523_frota_step07"
branch_labels = None
depends_on = None

_SCHEMA = "farms"


def upgrade() -> None:
    with op.batch_alter_table("frota_apontamentos_uso", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("jornada_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("safra_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("production_unit_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("area_ha_trabalhada", sa.Numeric(12, 4), nullable=True))
        batch_op.add_column(sa.Column("quantidade_produzida", sa.Numeric(18, 6), nullable=True))
        batch_op.add_column(sa.Column("quantidade_aplicada", sa.Numeric(18, 6), nullable=True))
        batch_op.add_column(sa.Column("custo_total", sa.Numeric(15, 2), nullable=True))
        batch_op.add_column(sa.Column("custo_por_ha", sa.Numeric(15, 4), nullable=True))
        batch_op.create_index("ix_frota_apontamentos_uso_jornada_id", ["jornada_id"])
        batch_op.create_index("ix_frota_apontamentos_uso_safra_id", ["safra_id"])
        batch_op.create_index("ix_frota_apontamentos_uso_production_unit_id", ["production_unit_id"])
        batch_op.create_index("ix_frota_apontamentos_uso_operador_id", ["operador_id"])
        batch_op.create_index("ix_frota_apontamentos_uso_operacao_id", ["operacao_id"])
        batch_op.create_foreign_key(
            "frota_apontamentos_uso_jornada_id_fkey",
            "frota_jornadas_equipamento",
            ["jornada_id"],
            ["id"],
            source_schema=_SCHEMA,
            referent_schema=_SCHEMA,
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "frota_apontamentos_uso_safra_id_fkey",
            "safras",
            ["safra_id"],
            ["id"],
            source_schema=_SCHEMA,
            referent_schema=_SCHEMA,
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "frota_apontamentos_uso_production_unit_id_fkey",
            "production_units",
            ["production_unit_id"],
            ["id"],
            source_schema=_SCHEMA,
            referent_schema=_SCHEMA,
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("frota_apontamentos_uso", schema=_SCHEMA) as batch_op:
        batch_op.drop_constraint("frota_apontamentos_uso_production_unit_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("frota_apontamentos_uso_safra_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("frota_apontamentos_uso_jornada_id_fkey", type_="foreignkey")
        batch_op.drop_index("ix_frota_apontamentos_uso_operacao_id")
        batch_op.drop_index("ix_frota_apontamentos_uso_operador_id")
        batch_op.drop_index("ix_frota_apontamentos_uso_production_unit_id")
        batch_op.drop_index("ix_frota_apontamentos_uso_safra_id")
        batch_op.drop_index("ix_frota_apontamentos_uso_jornada_id")
        batch_op.drop_column("custo_por_ha")
        batch_op.drop_column("custo_total")
        batch_op.drop_column("quantidade_aplicada")
        batch_op.drop_column("quantidade_produzida")
        batch_op.drop_column("area_ha_trabalhada")
        batch_op.drop_column("production_unit_id")
        batch_op.drop_column("safra_id")
        batch_op.drop_column("jornada_id")
