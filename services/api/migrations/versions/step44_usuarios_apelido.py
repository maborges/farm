"""step44 — adiciona apelido em usuarios"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "step44_usuarios_apelido"
down_revision = "step43_lancamentos_origem"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("usuarios")}
    if "apelido" not in columns:
        op.add_column(
            "usuarios",
            sa.Column("apelido", sa.String(length=20), nullable=True),
        )
    op.execute("COMMIT")


def downgrade():
    op.drop_column("usuarios", "apelido")
