"""frota equipamento alocacoes

Revision ID: 20260518_frota_alocacoes
Revises: 20260507_frota_jornadas
Create Date: 2026-05-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260518_frota_alocacoes"
down_revision: Union[str, Sequence[str], None] = "20260507_frota_jornadas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "equipamento_alocacoes" in inspector.get_table_names():
        return

    op.create_table(
        "equipamento_alocacoes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("equipamento_id", sa.Uuid(), nullable=False),
        sa.Column("unidade_produtiva_id", sa.Uuid(), nullable=False),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("principal", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ATIVA"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("responsavel_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["equipamento_id"], ["cadastros_equipamentos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["unidades_produtivas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsavel_id"], ["cadastros_pessoas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("equipamento_alocacoes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_equipamento_alocacoes_tenant_id"), ["tenant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_equipamento_alocacoes_equipamento_id"), ["equipamento_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_equipamento_alocacoes_unidade_produtiva_id"), ["unidade_produtiva_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_equipamento_alocacoes_data_inicio"), ["data_inicio"], unique=False)
        batch_op.create_index(batch_op.f("ix_equipamento_alocacoes_data_fim"), ["data_fim"], unique=False)
        batch_op.create_index(batch_op.f("ix_equipamento_alocacoes_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_equipamento_alocacoes_responsavel_id"), ["responsavel_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "equipamento_alocacoes" not in inspector.get_table_names():
        return

    with op.batch_alter_table("equipamento_alocacoes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_equipamento_alocacoes_responsavel_id"))
        batch_op.drop_index(batch_op.f("ix_equipamento_alocacoes_status"))
        batch_op.drop_index(batch_op.f("ix_equipamento_alocacoes_data_fim"))
        batch_op.drop_index(batch_op.f("ix_equipamento_alocacoes_data_inicio"))
        batch_op.drop_index(batch_op.f("ix_equipamento_alocacoes_unidade_produtiva_id"))
        batch_op.drop_index(batch_op.f("ix_equipamento_alocacoes_equipamento_id"))
        batch_op.drop_index(batch_op.f("ix_equipamento_alocacoes_tenant_id"))
    op.drop_table("equipamento_alocacoes")
