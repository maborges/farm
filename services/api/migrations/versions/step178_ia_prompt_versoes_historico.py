"""step178: cria tabela ia_prompt_versoes_historico

Revision ID: step178
Revises: step177
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "step178"
down_revision = "step177"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_prompt_versoes_historico",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column(
            "prompt_versao_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("ia_prompts_versoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("tipo_evento", sa.String(20), nullable=False),
        sa.Column("valor_anterior", sa.JSON(), nullable=True),
        sa.Column("valor_novo", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_ia_prompt_vers_hist_prompt",
        "ia_prompt_versoes_historico",
        ["prompt_versao_id", "created_at"],
    )
    op.create_index(
        "ix_ia_prompt_vers_hist_tenant",
        "ia_prompt_versoes_historico",
        ["tenant_id", "created_at"],
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_ia_prompt_vers_hist_tenant", table_name="ia_prompt_versoes_historico")
    op.drop_index("ix_ia_prompt_vers_hist_prompt", table_name="ia_prompt_versoes_historico")
    op.drop_table("ia_prompt_versoes_historico")
