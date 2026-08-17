"""balanca avaliacao de prestador (transportador/motorista)

Revision ID: 20260817_balanca_avaliacao_prestador
Revises: 20260817_balanca_ajuste_qualidade
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260817_balanca_avaliacao_prestador"
down_revision = "20260817_balanca_ajuste_qualidade"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "balanca_avaliacoes_prestador",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ordem_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("balanca_ordens.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tipo_identificador", sa.String(15), nullable=False),
        sa.Column("identificador", sa.String(150), nullable=False, index=True),
        sa.Column("nota", sa.Integer, nullable=False),
        sa.Column("comentario", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_balanca_avaliacao_identificador",
        "balanca_avaliacoes_prestador",
        ["tenant_id", "tipo_identificador", "identificador"],
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_balanca_avaliacao_identificador", table_name="balanca_avaliacoes_prestador")
    op.drop_table("balanca_avaliacoes_prestador")
    op.execute("COMMIT")
