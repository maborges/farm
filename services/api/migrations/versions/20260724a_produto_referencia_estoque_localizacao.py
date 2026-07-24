"""Produto por cópia de referência + localização física de estoque.

- Adiciona cadastros_produtos.produto_referencia_id (FK opcional para o
  próprio produto padrão do sistema, tenant_id NULL) — usado quando o tenant
  cria um produto a partir de um padrão, mantendo o vínculo só para análise
  comparativa entre tenants (não sincroniza; unidade_medida trava na criação
  a nível de schema/aplicação, não de banco).
- Adiciona estoque_saldos.estoque_maximo (espelha estoque_minimo já existente).
- Cria estoque_localizacoes: endereço físico (corredor/prateleira/posição +
  texto livre) do produto dentro do depósito, permitindo múltiplas
  localizações por produto/depósito.

Revision ID: 20260724a_prodref_estloc
Revises: 20260723f_categoria_plano
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = "20260724a_prodref_estloc"
down_revision = "20260723f_categoria_plano"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cadastros_produtos",
        sa.Column("produto_referencia_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_produto_referencia",
        "cadastros_produtos", "cadastros_produtos",
        ["produto_referencia_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_cadastros_produtos_produto_referencia_id",
        "cadastros_produtos", ["produto_referencia_id"],
    )

    op.add_column(
        "estoque_saldos",
        sa.Column("estoque_maximo", sa.Numeric(18, 6), nullable=True),
    )

    op.create_table(
        "estoque_localizacoes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("deposito_id", sa.Uuid(), sa.ForeignKey("estoque_depositos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("produto_id", sa.Uuid(), sa.ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("corredor", sa.String(20), nullable=True),
        sa.Column("prateleira", sa.String(20), nullable=True),
        sa.Column("posicao", sa.String(20), nullable=True),
        sa.Column("codigo_localizacao", sa.String(50), nullable=True),
        sa.Column("observacao_livre", sa.String(200), nullable=True),
        sa.Column("quantidade", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_estoque_localizacoes_codigo_localizacao", "estoque_localizacoes", ["codigo_localizacao"])
    op.create_index("ix_estloc_produto_deposito", "estoque_localizacoes", ["produto_id", "deposito_id"])

    op.execute("COMMIT")


def downgrade():
    op.drop_table("estoque_localizacoes")
    op.drop_column("estoque_saldos", "estoque_maximo")
    op.drop_index("ix_cadastros_produtos_produto_referencia_id", table_name="cadastros_produtos")
    op.drop_constraint("fk_produto_referencia", "cadastros_produtos", type_="foreignkey")
    op.drop_column("cadastros_produtos", "produto_referencia_id")
