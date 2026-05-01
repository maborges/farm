"""step28: cria tabela financeiro_lancamentos

Revision ID: step28_financeiro_lancamentos
Revises: step27_tenant_documento_nullable, step27_rename_insumo_id
Create Date: 2026-05-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "step28_financeiro_lancamentos"
down_revision = ("step27_tenant_documento_nullable", "step27_rename_insumo_id")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financeiro_lancamentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="SET NULL"), nullable=True),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("data", sa.Date, nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False, server_default="CUSTO"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_fin_lancamentos_tenant", "financeiro_lancamentos", ["tenant_id"])
    op.create_index("ix_fin_lancamentos_safra", "financeiro_lancamentos", ["safra_id"])


def downgrade():
    op.drop_index("ix_fin_lancamentos_safra", "financeiro_lancamentos")
    op.drop_index("ix_fin_lancamentos_tenant", "financeiro_lancamentos")
    op.drop_table("financeiro_lancamentos")
