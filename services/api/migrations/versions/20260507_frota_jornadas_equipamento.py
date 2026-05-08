"""frota_jornadas_equipamento

Revision ID: 20260507_frota_jornadas
Revises: 20260507_frota_disponibilidade
Create Date: 2026-05-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260507_frota_jornadas"
down_revision: Union[str, Sequence[str], None] = "20260507_frota_disponibilidade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "frota_jornadas_equipamento",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("equipamento_id", sa.Uuid(), nullable=False),
        sa.Column("operador_id", sa.Uuid(), nullable=True),
        sa.Column("unidade_produtiva_id", sa.Uuid(), nullable=True),
        sa.Column("safra_id", sa.Uuid(), nullable=True),
        sa.Column("talhao_id", sa.Uuid(), nullable=True),
        sa.Column("tipo_operacao", sa.String(length=80), nullable=False),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("horimetro_inicial", sa.Float(), nullable=True),
        sa.Column("horimetro_final", sa.Float(), nullable=True),
        sa.Column("km_inicial", sa.Float(), nullable=True),
        sa.Column("km_final", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["equipamento_id"], ["cadastros_equipamentos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operador_id"], ["cadastros_pessoas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["unidades_produtivas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["safra_id"], ["safras.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["talhao_id"], ["cadastros_areas_rurais.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("frota_jornadas_equipamento", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_tenant_id"), ["tenant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_equipamento_id"), ["equipamento_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_operador_id"), ["operador_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_unidade_produtiva_id"), ["unidade_produtiva_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_safra_id"), ["safra_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_talhao_id"), ["talhao_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_tipo_operacao"), ["tipo_operacao"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_data_inicio"), ["data_inicio"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_data_fim"), ["data_fim"], unique=False)
        batch_op.create_index(batch_op.f("ix_frota_jornadas_equipamento_status"), ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("frota_jornadas_equipamento", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_status"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_data_fim"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_data_inicio"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_tipo_operacao"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_talhao_id"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_safra_id"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_unidade_produtiva_id"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_operador_id"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_equipamento_id"))
        batch_op.drop_index(batch_op.f("ix_frota_jornadas_equipamento_tenant_id"))
    op.drop_table("frota_jornadas_equipamento")
