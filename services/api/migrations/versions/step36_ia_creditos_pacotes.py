"""step36: ia_creditos_pacotes — créditos extras de IA por tenant

Revision ID: step36_ia_creditos_pacotes
Revises: step35_ia_uso
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "step36_ia_creditos_pacotes"
down_revision = "step35_ia_uso"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_creditos_pacotes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantidade_creditos", sa.Integer, nullable=False),
        sa.Column("creditos_usados", sa.Integer, nullable=False, server_default="0"),
        sa.Column("origem", sa.String(60), nullable=False, server_default="SOLICITACAO"),
        sa.Column("status", sa.String(10), nullable=False, server_default="ATIVO"),
        sa.Column("adquirido_em", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ia_creditos_tenant_status", "ia_creditos_pacotes", ["tenant_id", "status"])
    # Adiciona coluna fonte_consumo em ia_uso para rastrear PLANO vs PACOTE
    op.add_column("ia_uso", sa.Column("fonte_consumo", sa.String(10), nullable=True))


def downgrade():
    op.drop_column("ia_uso", "fonte_consumo")
    op.drop_index("ix_ia_creditos_tenant_status")
    op.drop_table("ia_creditos_pacotes")
