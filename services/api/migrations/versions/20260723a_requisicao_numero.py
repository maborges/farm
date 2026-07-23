"""adiciona numero (código de referência) em estoque_requisicoes

Revision ID: 20260723a_requisicao_numero
Revises: 20260722j_alocacoes_solicitante
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260723a_requisicao_numero"
down_revision = "20260722j_alocacoes_solicitante"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("estoque_requisicoes", sa.Column("numero", sa.String(30), nullable=True))
    op.create_index("ix_estoque_requisicoes_numero", "estoque_requisicoes", ["numero"], unique=False)
    op.create_unique_constraint(
        "uq_estoque_requisicoes_tenant_numero", "estoque_requisicoes", ["tenant_id", "numero"]
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_constraint("uq_estoque_requisicoes_tenant_numero", "estoque_requisicoes", type_="unique")
    op.drop_index("ix_estoque_requisicoes_numero", table_name="estoque_requisicoes")
    op.drop_column("estoque_requisicoes", "numero")
    op.execute("COMMIT")
