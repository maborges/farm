"""estoque_implantacao_confirmacao

Revision ID: 20260608_estoque_implantacao_confirmacao
Revises: 20260608_estoque_implantacao
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260608_estoque_implantacao_confirmacao"
down_revision = "20260608_estoque_implantacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    sessao_columns = {column["name"] for column in inspector.get_columns("estoque_implantacao_sessoes")}
    sessao_indexes = {index["name"] for index in inspector.get_indexes("estoque_implantacao_sessoes")}
    sessao_fks = {fk["name"] for fk in inspector.get_foreign_keys("estoque_implantacao_sessoes")}
    movimento_checks = {check["name"] for check in inspector.get_check_constraints("estoque_movimentos")}

    if "confirmado_por" not in sessao_columns:
        op.add_column("estoque_implantacao_sessoes", sa.Column("confirmado_por", sa.Uuid(), nullable=True))
    if "fk_estoque_implantacao_sessoes_confirmado_por" not in sessao_fks:
        op.create_foreign_key(
            "fk_estoque_implantacao_sessoes_confirmado_por",
            "estoque_implantacao_sessoes",
            "usuarios",
            ["confirmado_por"],
            ["id"],
            ondelete="SET NULL",
        )
    if "ix_estoque_implantacao_sessoes_confirmado_por" not in sessao_indexes:
        op.create_index(
            "ix_estoque_implantacao_sessoes_confirmado_por",
            "estoque_implantacao_sessoes",
            ["confirmado_por"],
        )

    if "ck_estoque_movimentos_origem" in movimento_checks:
        op.drop_constraint("ck_estoque_movimentos_origem", "estoque_movimentos", type_="check")
    op.execute(
        """
        ALTER TABLE estoque_movimentos
        ADD CONSTRAINT ck_estoque_movimentos_origem
        CHECK (
            origem IN (
                'OPERACAO_EXECUCAO',
                'COMPRA',
                'COLHEITA',
                'AJUSTE',
                'MANUAL',
                'TRANSFERENCIA',
                'LEGADO',
                'IMPLANTACAO'
            )
        ) NOT VALID
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_estoque_movimentos_origem", "estoque_movimentos", type_="check")
    op.execute(
        """
        ALTER TABLE estoque_movimentos
        ADD CONSTRAINT ck_estoque_movimentos_origem
        CHECK (
            origem IN (
                'OPERACAO_EXECUCAO',
                'COMPRA',
                'COLHEITA',
                'AJUSTE',
                'MANUAL',
                'TRANSFERENCIA',
                'LEGADO'
            )
        ) NOT VALID
        """
    )

    op.drop_index("ix_estoque_implantacao_sessoes_confirmado_por", table_name="estoque_implantacao_sessoes")
    op.drop_constraint("fk_estoque_implantacao_sessoes_confirmado_por", "estoque_implantacao_sessoes", type_="foreignkey")
    op.drop_column("estoque_implantacao_sessoes", "confirmado_por")
