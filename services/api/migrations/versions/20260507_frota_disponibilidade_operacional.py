"""add frota disponibilidade operacional fields

Revision ID: 20260507_frota_disponibilidade
Revises: 20260507_frota_preventiva
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa


revision = "20260507_frota_disponibilidade"
down_revision = "20260507_frota_preventiva"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("cadastros_equipamentos")}

    if "bloqueado_operacional" not in columns:
        op.add_column(
            "cadastros_equipamentos",
            sa.Column("bloqueado_operacional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "motivo_bloqueio_operacional" not in columns:
        op.add_column(
            "cadastros_equipamentos",
            sa.Column("motivo_bloqueio_operacional", sa.Text(), nullable=True),
        )
    if "bloqueado_operacional_em" not in columns:
        op.add_column(
            "cadastros_equipamentos",
            sa.Column("bloqueado_operacional_em", sa.DateTime(timezone=True), nullable=True),
        )
    if "liberado_operacional_em" not in columns:
        op.add_column(
            "cadastros_equipamentos",
            sa.Column("liberado_operacional_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("cadastros_equipamentos")}

    if "liberado_operacional_em" in columns:
        op.drop_column("cadastros_equipamentos", "liberado_operacional_em")
    if "bloqueado_operacional_em" in columns:
        op.drop_column("cadastros_equipamentos", "bloqueado_operacional_em")
    if "motivo_bloqueio_operacional" in columns:
        op.drop_column("cadastros_equipamentos", "motivo_bloqueio_operacional")
    if "bloqueado_operacional" in columns:
        op.drop_column("cadastros_equipamentos", "bloqueado_operacional")
