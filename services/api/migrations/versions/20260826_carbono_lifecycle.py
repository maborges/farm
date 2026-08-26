"""Add soft lifecycle flags to carbon records."""

from alembic import op
import sqlalchemy as sa


revision = "20260826_carbono_lifecycle"
down_revision = "20260826_carbono_unidade_produtiva"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add active flags without removing existing carbon records."""
    inspector = sa.inspect(op.get_bind())
    for table_name in ("carbono_emissoes", "carbono_projetos"):
        if table_name not in inspector.get_table_names():
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "ativo" not in columns:
            op.add_column(table_name, sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()))
        op.alter_column(table_name, "ativo", server_default=None)


def downgrade() -> None:
    """Remove lifecycle flags from carbon records."""
    inspector = sa.inspect(op.get_bind())
    for table_name in ("carbono_emissoes", "carbono_projetos"):
        if table_name in inspector.get_table_names():
            op.drop_column(table_name, "ativo")
