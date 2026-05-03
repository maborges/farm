"""step169_ia_compras_recomendacoes

Revision ID: step169
Revises:
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "step169"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_compras_recomendacoes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", UUID(as_uuid=True), nullable=True),
        sa.Column("item_id", UUID(as_uuid=True), nullable=True),
        sa.Column("solicitacao_id", UUID(as_uuid=True), nullable=True),
        sa.Column("estrategia", sa.String(30), nullable=False),
        sa.Column("resumo", sa.String(500), nullable=False),
        sa.Column("justificativas", JSONB, nullable=False, server_default="[]"),
        sa.Column("nivel_confianca", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("fonte", sa.String(20), nullable=False, server_default="DETERMINISTICO"),
        sa.Column("limite_atingido", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ia_compras_rec_tenant", "ia_compras_recomendacoes", ["tenant_id", "created_at"])
    op.create_index("ix_ia_compras_rec_solicitacao", "ia_compras_recomendacoes", ["solicitacao_id"])


def downgrade():
    op.drop_index("ix_ia_compras_rec_solicitacao")
    op.drop_index("ix_ia_compras_rec_tenant")
    op.drop_table("ia_compras_recomendacoes")
