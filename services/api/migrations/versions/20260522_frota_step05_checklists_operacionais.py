"""frota_step05_checklists_operacionais

Revision ID: 20260522_frota_step05
Revises: 20260521_frota_step04
Create Date: 2026-05-22 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260522_frota_step05"
down_revision = "20260521_frota_step04"
branch_labels = None
depends_on = None

_SCHEMA = "farms"


def upgrade() -> None:
    op.create_table(
        "frota_checklists_operacionais",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("tipo_equipamento", sa.String(length=30), nullable=True),
        sa.Column("tipo_jornada", sa.String(length=20), nullable=False),
        sa.Column("exige_antes_operacao", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bloqueia_falha_critica", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{_SCHEMA}.tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_frota_checklists_oper_tenant_tipo",
        "frota_checklists_operacionais",
        ["tenant_id", "tipo_equipamento", "tipo_jornada", "ativo"],
        schema=_SCHEMA,
    )

    op.create_table(
        "frota_checklists_operacionais_itens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("categoria", sa.String(length=30), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["checklist_id"], [f"{_SCHEMA}.frota_checklists_operacionais.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{_SCHEMA}.tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_frota_checklist_itens_tenant_checklist",
        "frota_checklists_operacionais_itens",
        ["tenant_id", "checklist_id"],
        schema=_SCHEMA,
    )

    op.create_table(
        "frota_checklists_operacionais_respostas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("equipamento_id", sa.Uuid(), nullable=False),
        sa.Column("jornada_id", sa.Uuid(), nullable=True),
        sa.Column("operador_id", sa.Uuid(), nullable=True),
        sa.Column("unidade_produtiva_id", sa.Uuid(), nullable=True),
        sa.Column("safra_id", sa.Uuid(), nullable=True),
        sa.Column("tipo_jornada", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("falha", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("criticidade", sa.String(length=20), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("alerta_operacional", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("os_gerada_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["checklist_id"], [f"{_SCHEMA}.frota_checklists_operacionais.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_id"], [f"{_SCHEMA}.frota_checklists_operacionais_itens.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["equipamento_id"], [f"{_SCHEMA}.cadastros_equipamentos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["jornada_id"], [f"{_SCHEMA}.frota_jornadas_equipamento.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operador_id"], [f"{_SCHEMA}.cadastros_pessoas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unidade_produtiva_id"], [f"{_SCHEMA}.unidades_produtivas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["safra_id"], [f"{_SCHEMA}.safras.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["os_gerada_id"], [f"{_SCHEMA}.frota_ordens_servico.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{_SCHEMA}.tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_frota_check_resp_tenant_equip_data",
        "frota_checklists_operacionais_respostas",
        ["tenant_id", "equipamento_id", "created_at"],
        schema=_SCHEMA,
    )
    op.create_index("ix_frota_check_resp_tenant_operador", "frota_checklists_operacionais_respostas", ["tenant_id", "operador_id"], schema=_SCHEMA)
    op.create_index("ix_frota_check_resp_tenant_up", "frota_checklists_operacionais_respostas", ["tenant_id", "unidade_produtiva_id"], schema=_SCHEMA)
    op.create_index("ix_frota_check_resp_tenant_safra", "frota_checklists_operacionais_respostas", ["tenant_id", "safra_id"], schema=_SCHEMA)

    with op.batch_alter_table("frota_ordens_servico", schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("origem_checklist_resposta_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_frota_ordens_servico_origem_checklist_resposta_id", ["origem_checklist_resposta_id"])


def downgrade() -> None:
    with op.batch_alter_table("frota_ordens_servico", schema=_SCHEMA) as batch_op:
        batch_op.drop_index("ix_frota_ordens_servico_origem_checklist_resposta_id")
        batch_op.drop_column("origem_checklist_resposta_id")
    op.drop_table("frota_checklists_operacionais_respostas", schema=_SCHEMA)
    op.drop_table("frota_checklists_operacionais_itens", schema=_SCHEMA)
    op.drop_table("frota_checklists_operacionais", schema=_SCHEMA)
