"""estoque_implantacao_sessoes

Revision ID: 20260608_estoque_implantacao
Revises: a4dc0640fdcf
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260608_estoque_implantacao"
down_revision = "a4dc0640fdcf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())
    existing_indexes = {
        table_name: {index["name"] for index in inspector.get_indexes(table_name)}
        for table_name in ("estoque_implantacao_sessoes", "estoque_implantacao_itens")
        if table_name in existing_tables
    }

    if "estoque_implantacao_sessoes" not in existing_tables:
        op.create_table(
            "estoque_implantacao_sessoes",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column("unidade_produtiva_id", sa.Uuid(), nullable=True),
            sa.Column("arquivo_nome", sa.String(length=255), nullable=False),
            sa.Column("arquivo_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("mapeamento_colunas", sa.JSON(), nullable=False),
            sa.Column("colunas_detectadas", sa.JSON(), nullable=False),
            sa.Column("total_linhas", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("linhas_validas", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("linhas_com_erro", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("linhas_com_aviso", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("valor_total_estimado", sa.Numeric(15, 2), nullable=False, server_default="0"),
            sa.Column("criado_por", sa.Uuid(), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
            sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("confirmado_em", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["unidades_produtivas.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["criado_por"], ["usuarios.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_indexes["estoque_implantacao_sessoes"] = set()

    if "ix_estoque_implantacao_sessoes_tenant_id" not in existing_indexes.get("estoque_implantacao_sessoes", set()):
        op.create_index("ix_estoque_implantacao_sessoes_tenant_id", "estoque_implantacao_sessoes", ["tenant_id"])
    if "ix_estoque_implantacao_sessoes_unidade_produtiva_id" not in existing_indexes.get("estoque_implantacao_sessoes", set()):
        op.create_index("ix_estoque_implantacao_sessoes_unidade_produtiva_id", "estoque_implantacao_sessoes", ["unidade_produtiva_id"])
    if "ix_estoque_implantacao_sessoes_status" not in existing_indexes.get("estoque_implantacao_sessoes", set()):
        op.create_index("ix_estoque_implantacao_sessoes_status", "estoque_implantacao_sessoes", ["status"])
    if "ix_estoque_implantacao_sessoes_arquivo_hash" not in existing_indexes.get("estoque_implantacao_sessoes", set()):
        op.create_index("ix_estoque_implantacao_sessoes_arquivo_hash", "estoque_implantacao_sessoes", ["arquivo_hash"])

    if "estoque_implantacao_itens" not in existing_tables:
        op.create_table(
            "estoque_implantacao_itens",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("sessao_id", sa.Uuid(), nullable=False),
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column("numero_linha", sa.Integer(), nullable=False),
            sa.Column("payload_original", sa.JSON(), nullable=False),
            sa.Column("dados_normalizados", sa.JSON(), nullable=False),
            sa.Column("produto_id_resolvido", sa.Uuid(), nullable=True),
            sa.Column("deposito_id_resolvido", sa.Uuid(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("erros", sa.JSON(), nullable=False),
            sa.Column("avisos", sa.JSON(), nullable=False),
            sa.Column("sugestoes", sa.JSON(), nullable=False),
            sa.Column("ignorado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
            sa.ForeignKeyConstraint(["sessao_id"], ["estoque_implantacao_sessoes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["produto_id_resolvido"], ["cadastros_produtos.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["deposito_id_resolvido"], ["estoque_depositos.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_indexes["estoque_implantacao_itens"] = set()

    if "ix_estoque_implantacao_itens_sessao_id" not in existing_indexes.get("estoque_implantacao_itens", set()):
        op.create_index("ix_estoque_implantacao_itens_sessao_id", "estoque_implantacao_itens", ["sessao_id"])
    if "ix_estoque_implantacao_itens_tenant_id" not in existing_indexes.get("estoque_implantacao_itens", set()):
        op.create_index("ix_estoque_implantacao_itens_tenant_id", "estoque_implantacao_itens", ["tenant_id"])
    if "ix_estoque_implantacao_itens_status" not in existing_indexes.get("estoque_implantacao_itens", set()):
        op.create_index("ix_estoque_implantacao_itens_status", "estoque_implantacao_itens", ["status"])
    if "ix_estoque_implantacao_itens_produto_id_resolvido" not in existing_indexes.get("estoque_implantacao_itens", set()):
        op.create_index("ix_estoque_implantacao_itens_produto_id_resolvido", "estoque_implantacao_itens", ["produto_id_resolvido"])
    if "ix_estoque_implantacao_itens_deposito_id_resolvido" not in existing_indexes.get("estoque_implantacao_itens", set()):
        op.create_index("ix_estoque_implantacao_itens_deposito_id_resolvido", "estoque_implantacao_itens", ["deposito_id_resolvido"])


def downgrade() -> None:
    op.drop_index("ix_estoque_implantacao_itens_deposito_id_resolvido", table_name="estoque_implantacao_itens")
    op.drop_index("ix_estoque_implantacao_itens_produto_id_resolvido", table_name="estoque_implantacao_itens")
    op.drop_index("ix_estoque_implantacao_itens_status", table_name="estoque_implantacao_itens")
    op.drop_index("ix_estoque_implantacao_itens_tenant_id", table_name="estoque_implantacao_itens")
    op.drop_index("ix_estoque_implantacao_itens_sessao_id", table_name="estoque_implantacao_itens")
    op.drop_table("estoque_implantacao_itens")

    op.drop_index("ix_estoque_implantacao_sessoes_arquivo_hash", table_name="estoque_implantacao_sessoes")
    op.drop_index("ix_estoque_implantacao_sessoes_status", table_name="estoque_implantacao_sessoes")
    op.drop_index("ix_estoque_implantacao_sessoes_unidade_produtiva_id", table_name="estoque_implantacao_sessoes")
    op.drop_index("ix_estoque_implantacao_sessoes_tenant_id", table_name="estoque_implantacao_sessoes")
    op.drop_table("estoque_implantacao_sessoes")
