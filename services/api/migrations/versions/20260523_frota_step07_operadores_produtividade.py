"""frota_step07_operadores_produtividade

Revision ID: 20260523_frota_step07
Revises: 20260522_frota_step05
Create Date: 2026-05-23 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260523_frota_step07"
down_revision = "20260522_frota_step05"
branch_labels = None
depends_on = None

_SCHEMA = "farms"


def upgrade() -> None:
    with op.batch_alter_table("frota_jornadas_equipamento", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("aberta_por_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("encerrada_por_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_frota_jornadas_aberta_por_id", ["aberta_por_id"])
        batch_op.create_index("ix_frota_jornadas_encerrada_por_id", ["encerrada_por_id"])

    with op.batch_alter_table("frota_ordens_servico", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("aberta_por_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("encerrada_por_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_frota_os_aberta_por_id", ["aberta_por_id"])
        batch_op.create_index("ix_frota_os_encerrada_por_id", ["encerrada_por_id"])

    with op.batch_alter_table("frota_os_itens", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("deposito_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("lote_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("unidade_produtiva_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("safra_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("custo_unitario", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("custo_total", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("movimento_estoque_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("executado_por_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_frota_os_itens_tenant", ["tenant_id"])
        batch_op.create_index("ix_frota_os_itens_deposito", ["deposito_id"])
        batch_op.create_index("ix_frota_os_itens_lote", ["lote_id"])
        batch_op.create_index("ix_frota_os_itens_up", ["unidade_produtiva_id"])
        batch_op.create_index("ix_frota_os_itens_safra", ["safra_id"])
        batch_op.create_index("ix_frota_os_itens_mov_estoque", ["movimento_estoque_id"])

    with op.batch_alter_table("frota_registros_manutencao", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("executado_por_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_frota_reg_manut_executado_por_id", ["executado_por_id"])

    with op.batch_alter_table("frota_checklists_operacionais_respostas", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("executado_por_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("reportado_por_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_frota_check_resp_exec_por", ["executado_por_id"])
        batch_op.create_index("ix_frota_check_resp_report_por", ["reportado_por_id"])


def downgrade() -> None:
    with op.batch_alter_table("frota_checklists_operacionais_respostas", schema=_SCHEMA) as batch_op:
        batch_op.drop_index("ix_frota_check_resp_report_por")
        batch_op.drop_index("ix_frota_check_resp_exec_por")
        batch_op.drop_column("reportado_por_id")
        batch_op.drop_column("executado_por_id")

    with op.batch_alter_table("frota_registros_manutencao", schema=_SCHEMA) as batch_op:
        batch_op.drop_index("ix_frota_reg_manut_executado_por_id")
        batch_op.drop_column("executado_por_id")

    with op.batch_alter_table("frota_os_itens", schema=_SCHEMA) as batch_op:
        batch_op.drop_index("ix_frota_os_itens_mov_estoque")
        batch_op.drop_index("ix_frota_os_itens_safra")
        batch_op.drop_index("ix_frota_os_itens_up")
        batch_op.drop_index("ix_frota_os_itens_lote")
        batch_op.drop_index("ix_frota_os_itens_deposito")
        batch_op.drop_index("ix_frota_os_itens_tenant")
        batch_op.drop_column("executado_por_id")
        batch_op.drop_column("movimento_estoque_id")
        batch_op.drop_column("custo_total")
        batch_op.drop_column("custo_unitario")
        batch_op.drop_column("safra_id")
        batch_op.drop_column("unidade_produtiva_id")
        batch_op.drop_column("lote_id")
        batch_op.drop_column("deposito_id")
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("frota_ordens_servico", schema=_SCHEMA) as batch_op:
        batch_op.drop_index("ix_frota_os_encerrada_por_id")
        batch_op.drop_index("ix_frota_os_aberta_por_id")
        batch_op.drop_column("encerrada_por_id")
        batch_op.drop_column("aberta_por_id")

    with op.batch_alter_table("frota_jornadas_equipamento", schema=_SCHEMA) as batch_op:
        batch_op.drop_index("ix_frota_jornadas_encerrada_por_id")
        batch_op.drop_index("ix_frota_jornadas_aberta_por_id")
        batch_op.drop_column("encerrada_por_id")
        batch_op.drop_column("aberta_por_id")
