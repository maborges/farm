"""step35: ia_uso — rastreio de consumo de IA por tenant

Revision ID: step35_ia_uso
Revises: step34_automacoes_agendamento
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "step35_ia_uso"
down_revision = "step34_automacoes_agendamento"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_uso",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("origem", sa.String(60), nullable=False),
        sa.Column("modelo", sa.String(60), nullable=True),
        sa.Column("tokens_entrada", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_saida", sa.Integer, nullable=False, server_default="0"),
        sa.Column("custo_estimado", sa.Numeric(10, 6), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="SUCESSO"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ia_uso_tenant_created", "ia_uso", ["tenant_id", "created_at"])


def downgrade():
    op.drop_index("ix_ia_uso_tenant_created")
    op.drop_table("ia_uso")
