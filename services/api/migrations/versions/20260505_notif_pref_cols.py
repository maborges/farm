"""add missing notificacoes_preferencias columns

Revision ID: 20260505_notif_cols
Revises: 20260505_ia_ux
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260505_notif_cols"
down_revision = "20260505_ia_ux"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("notificacoes_preferencias")}

    if "whatsapp_ativo" not in columns:
        op.add_column(
            "notificacoes_preferencias",
            sa.Column("whatsapp_ativo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    if "horario_envio" not in columns:
        op.add_column(
            "notificacoes_preferencias",
            sa.Column("horario_envio", sa.String(length=5), nullable=False, server_default="07:00"),
        )

    if "nivel_sensibilidade" not in columns:
        op.add_column(
            "notificacoes_preferencias",
            sa.Column("nivel_sensibilidade", sa.String(length=20), nullable=False, server_default="ALTO"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("notificacoes_preferencias")}

    if "nivel_sensibilidade" in columns:
        op.drop_column("notificacoes_preferencias", "nivel_sensibilidade")

    if "horario_envio" in columns:
        op.drop_column("notificacoes_preferencias", "horario_envio")

    if "whatsapp_ativo" in columns:
        op.drop_column("notificacoes_preferencias", "whatsapp_ativo")
