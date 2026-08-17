"""balanca fisica (equipamento) + afericoes (metrologia legal)

Revision ID: 20260817_balanca_fisica_afericao
Revises: 20260817_balanca_compras_vendas
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260817_balanca_fisica_afericao"
down_revision = "20260817_balanca_compras_vendas"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "balanca_fisicas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("unidade_produtiva_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("fabricante", sa.String(100), nullable=True),
        sa.Column("modelo", sa.String(100), nullable=True),
        sa.Column("numero_serie", sa.String(100), nullable=True),
        sa.Column("capacidade_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("ativa", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_balanca_fisica_tenant", "balanca_fisicas", ["tenant_id"])

    op.create_table(
        "balanca_afericoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("balanca_fisica_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("balanca_fisicas.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("data_afericao", sa.DateTime, nullable=False),
        sa.Column("validade_ate", sa.DateTime, nullable=True),
        sa.Column("orgao_afericao", sa.String(150), nullable=True),
        sa.Column("numero_certificado", sa.String(100), nullable=True),
        sa.Column("resultado", sa.String(30), nullable=False, server_default="APROVADA"),
        sa.Column("observacoes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_balanca_afericao_balanca", "balanca_afericoes", ["balanca_fisica_id", "data_afericao"])

    op.add_column(
        "balanca_dispositivos",
        sa.Column("balanca_fisica_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("balanca_fisicas.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_balanca_disp_balanca_fisica", "balanca_dispositivos", ["balanca_fisica_id"])

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_balanca_disp_balanca_fisica", table_name="balanca_dispositivos")
    op.drop_column("balanca_dispositivos", "balanca_fisica_id")
    op.drop_index("ix_balanca_afericao_balanca", table_name="balanca_afericoes")
    op.drop_table("balanca_afericoes")
    op.drop_index("ix_balanca_fisica_tenant", table_name="balanca_fisicas")
    op.drop_table("balanca_fisicas")
    op.execute("COMMIT")
