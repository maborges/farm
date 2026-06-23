"""
EXEC-37 — Adiciona campos fundiários expandidos

ImovelRural: sigef_codigo
UnidadeProdutiva: numero_matricula (campo legado de compatibilidade)

Revision ID: exec37_fundiario_fields
Revises: stepGrowth25
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "exec37_fundiario_fields"
down_revision = "db819dde310d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ImovelRural — adiciona sigef_codigo (índice para busca de convergência)
    op.add_column(
        "imoveis_rurais",
        sa.Column("sigef_codigo", sa.String(50), nullable=True, comment="Código SIGEF (INCRA georreferenciamento)"),
    )
    op.create_index("ix_imoveis_rurais_sigef_codigo", "imoveis_rurais", ["sigef_codigo"])

    # UnidadeProdutiva — adiciona numero_matricula (campo legado / compatibilidade)
    op.add_column(
        "unidades_produtivas",
        sa.Column("numero_matricula", sa.String(100), nullable=True, comment="Matrícula legada"),
    )


def downgrade() -> None:
    op.drop_column("unidades_produtivas", "numero_matricula")
    op.drop_index("ix_imoveis_rurais_sigef_codigo", table_name="imoveis_rurais")
    op.drop_column("imoveis_rurais", "sigef_codigo")
