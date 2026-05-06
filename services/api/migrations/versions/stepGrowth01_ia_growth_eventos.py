"""stepGrowth01_ia_growth_eventos

Revision ID: stepGrowth01
Revises: step194
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "stepGrowth01"
down_revision = "step194"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_growth_eventos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", UUID(as_uuid=True), nullable=True),
        sa.Column("evento", sa.String(60), nullable=False),   # upgrade_cta_viewed | upgrade_cta_clicked
        sa.Column("tipo_cta", sa.String(40), nullable=True),  # UPGRADE_PLANO | CREDITOS_IA | ESPECIALISTA
        sa.Column("contexto", sa.String(40), nullable=True),  # progresso | acao | resumo
        sa.Column("metadados", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ia_growth_tenant_evento", "ia_growth_eventos", ["tenant_id", "evento", "created_at"])
    op.create_index("ix_ia_growth_usuario", "ia_growth_eventos", ["usuario_id", "created_at"])


def downgrade():
    op.drop_index("ix_ia_growth_usuario")
    op.drop_index("ix_ia_growth_tenant_evento")
    op.drop_table("ia_growth_eventos")
