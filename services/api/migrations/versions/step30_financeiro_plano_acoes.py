"""step30: financeiro_plano_acoes

Revision ID: step30_financeiro_plano_acoes
Revises: step29_lancamento_categoria
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "step30_financeiro_plano_acoes"
down_revision = "step29_lancamento_categoria"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financeiro_plano_acoes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_id", sa.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(60), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("descricao", sa.String(500), nullable=False),
        sa.Column("prioridade", sa.String(10), nullable=False, server_default="MEDIA"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.Column("rota", sa.String(200), nullable=False),
        sa.Column("origem", sa.String(30), nullable=False, server_default="AUTO"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("concluido_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ignorado_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_plano_acoes_tenant_safra", "financeiro_plano_acoes", ["tenant_id", "safra_id"])
    op.create_index("ix_plano_acoes_tipo_safra", "financeiro_plano_acoes", ["safra_id", "tipo"])


def downgrade():
    op.drop_index("ix_plano_acoes_tipo_safra")
    op.drop_index("ix_plano_acoes_tenant_safra")
    op.drop_table("financeiro_plano_acoes")
