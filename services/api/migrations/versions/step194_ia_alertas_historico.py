"""step194_ia_alertas_historico

Revision ID: step194
Revises: 518da168868d
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "step194"
down_revision = "518da168868d"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "ia_alertas_historico",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tipo_alerta", sa.String(60), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("mensagem", sa.Text, nullable=False),
        sa.Column("gravidade", sa.String(20), nullable=False),
        sa.Column("parametros_json", JSONB, nullable=True),
        sa.Column("visualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acao_executada", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acao_executada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ignorado", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ignorado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ia_alertas_hist_tenant", "ia_alertas_historico", ["tenant_id", "created_at"])
    op.create_index("ix_ia_alertas_hist_safra", "ia_alertas_historico", ["safra_id"])

def downgrade():
    op.drop_index("ix_ia_alertas_hist_safra")
    op.drop_index("ix_ia_alertas_hist_tenant")
    op.drop_table("ia_alertas_historico")
