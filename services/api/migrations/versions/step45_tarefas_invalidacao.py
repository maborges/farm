"""step45 — adiciona campos de invalidacao em safra_tarefas"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "step45_tarefas_invalidacao"
down_revision = "step44_usuarios_apelido"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("safra_tarefas")}
    if "invalidado_por" not in columns:
        op.add_column("safra_tarefas", sa.Column("invalidado_por", sa.Uuid(), nullable=True))
    if "invalidado_em" not in columns:
        op.add_column("safra_tarefas", sa.Column("invalidado_em", sa.DateTime(), nullable=True))
    if "motivo_invalidacao" not in columns:
        op.add_column("safra_tarefas", sa.Column("motivo_invalidacao", sa.Text(), nullable=True))
    op.execute("COMMIT")


def downgrade():
    op.drop_column("safra_tarefas", "motivo_invalidacao")
    op.drop_column("safra_tarefas", "invalidado_em")
    op.drop_column("safra_tarefas", "invalidado_por")
