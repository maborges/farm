"""step177: cria tabela ia_prompts_versoes para controle de versão do prompt

Revision ID: step177
Revises: step174
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "step177"
down_revision = "step174"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_prompts_versoes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("contexto", sa.String(60), nullable=False),
        sa.Column("versao", sa.String(20), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_ia_prompts_tenant_contexto", "ia_prompts_versoes", ["tenant_id", "contexto"])
    op.create_index("ix_ia_prompts_contexto_ativo", "ia_prompts_versoes", ["contexto", "ativo"])
    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_ia_prompts_contexto_ativo", table_name="ia_prompts_versoes")
    op.drop_index("ix_ia_prompts_tenant_contexto", table_name="ia_prompts_versoes")
    op.drop_table("ia_prompts_versoes")
