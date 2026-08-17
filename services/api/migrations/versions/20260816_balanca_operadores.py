"""balanca: cadastro de operadores com PIN pessoal (login em terminal compartilhado)

Revision ID: 20260816_balanca_operadores
Revises: 20260816_balanca_etapas
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260816_balanca_operadores"
down_revision = "20260816_balanca_etapas"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "balanca_operadores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pessoa_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nome_exibicao", sa.String(150), nullable=False),
        sa.Column("pin_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ATIVO"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by", UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "pessoa_id", name="uq_balanca_operador_tenant_pessoa"),
    )
    op.create_index("ix_balanca_operadores_tenant_id", "balanca_operadores", ["tenant_id"])
    op.create_index("ix_balanca_operadores_pessoa_id", "balanca_operadores", ["pessoa_id"])
    op.create_index("ix_balanca_operadores_tenant_status", "balanca_operadores", ["tenant_id", "status"])

    op.execute("COMMIT")


def downgrade():
    op.drop_table("balanca_operadores")
    op.execute("COMMIT")
