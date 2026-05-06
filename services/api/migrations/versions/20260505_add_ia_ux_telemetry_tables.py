"""add ia ux telemetry tables

Revision ID: 20260505_ia_ux
Revises: 89f49f7a692e
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260505_ia_ux"
down_revision = "89f49f7a692e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ia_ux_telemetria",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("evento", sa.String(length=50), nullable=False),
        sa.Column("modo", sa.String(length=20), nullable=False),
        sa.Column("sessao_id", sa.String(length=100), nullable=True),
        sa.Column("metadados", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ia_ux_telemetria_tenant_evento",
        "ia_ux_telemetria",
        ["tenant_id", "evento", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ia_ux_telemetria_evento",
        "ia_ux_telemetria",
        ["evento"],
        unique=False,
    )

    op.create_table(
        "ia_ux_thresholds",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("valor", sa.Float(), nullable=False),
        sa.Column("valor_padrao", sa.Float(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chave"),
    )
    op.create_index(
        "ix_ia_ux_thresholds_chave",
        "ia_ux_thresholds",
        ["chave"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ia_ux_thresholds_chave", table_name="ia_ux_thresholds")
    op.drop_table("ia_ux_thresholds")
    op.drop_index("ix_ia_ux_telemetria_evento", table_name="ia_ux_telemetria")
    op.drop_index("ix_ia_ux_telemetria_tenant_evento", table_name="ia_ux_telemetria")
    op.drop_table("ia_ux_telemetria")
