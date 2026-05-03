"""step31: extend notificacoes with nivel, origem, origem_id, read_at

Revision ID: step31_notificacoes_extend
Revises: step30_financeiro_plano_acoes
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "step31_notificacoes_extend"
down_revision = "step30_financeiro_plano_acoes"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notificacoes") as batch:
        batch.add_column(sa.Column("nivel", sa.String(10), nullable=False, server_default="INFO"))
        batch.add_column(sa.Column("origem", sa.String(60), nullable=True))
        batch.add_column(sa.Column("origem_id", sa.String(100), nullable=True))
        batch.add_column(sa.Column("usuario_id", sa.UUID(as_uuid=True), nullable=True))
        batch.add_column(sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_notificacoes_tenant_lida", "notificacoes", ["tenant_id", "lida"])
    op.create_index("ix_notificacoes_origem", "notificacoes", ["origem", "origem_id"])


def downgrade():
    op.drop_index("ix_notificacoes_origem")
    op.drop_index("ix_notificacoes_tenant_lida")
    with op.batch_alter_table("notificacoes") as batch:
        batch.drop_column("read_at")
        batch.drop_column("usuario_id")
        batch.drop_column("origem_id")
        batch.drop_column("origem")
        batch.drop_column("nivel")
