"""adiciona numero (código de referência) em compras_solicitacoes

Revision ID: 20260723b_solicitacao_numero
Revises: 20260723a_requisicao_numero
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260723b_solicitacao_numero"
down_revision = "20260723a_requisicao_numero"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("compras_solicitacoes", sa.Column("numero", sa.String(30), nullable=True))
    op.create_index("ix_compras_solicitacoes_numero", "compras_solicitacoes", ["numero"], unique=False)
    op.create_unique_constraint(
        "uq_compras_solicitacoes_tenant_numero", "compras_solicitacoes", ["tenant_id", "numero"]
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_constraint("uq_compras_solicitacoes_tenant_numero", "compras_solicitacoes", type_="unique")
    op.drop_index("ix_compras_solicitacoes_numero", table_name="compras_solicitacoes")
    op.drop_column("compras_solicitacoes", "numero")
    op.execute("COMMIT")
