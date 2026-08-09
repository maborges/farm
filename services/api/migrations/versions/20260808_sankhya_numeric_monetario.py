"""Converte colunas monetárias/fiscais do Sankhya de Float para Numeric(15,2)

Colunas afetadas: sankhya_produtos.preco_custo/preco_venda,
sankhya_nfe.valor_* (9 colunas), sankhya_lancamentos_financeiros.valor/valor_saldo.
Evita erro de arredondamento binário em dados fiscais/financeiros sincronizados do ERP.

Revision ID: 20260808_sankhya_numeric_monetario
Revises: 20260803_checklist_proc
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa

revision = "20260808_sankhya_numeric_monetario"
down_revision = "20260803_checklist_proc"
branch_labels = None
depends_on = None

_PRODUTO_COLUNAS = ("preco_custo", "preco_venda")
_NFE_COLUNAS = (
    "valor_total",
    "valor_produtos",
    "valor_frete",
    "valor_seguro",
    "valor_desconto",
    "valor_ipi",
    "valor_icms",
    "valor_pis",
    "valor_cofins",
)
_LANCAMENTO_COLUNAS = ("valor", "valor_saldo")


def upgrade():
    for coluna in _PRODUTO_COLUNAS:
        op.alter_column(
            "sankhya_produtos",
            coluna,
            type_=sa.Numeric(15, 2),
            existing_type=sa.Float(),
        )
    for coluna in _NFE_COLUNAS:
        op.alter_column(
            "sankhya_nfe",
            coluna,
            type_=sa.Numeric(15, 2),
            existing_type=sa.Float(),
        )
    for coluna in _LANCAMENTO_COLUNAS:
        op.alter_column(
            "sankhya_lancamentos_financeiros",
            coluna,
            type_=sa.Numeric(15, 2),
            existing_type=sa.Float(),
            existing_nullable=(coluna != "valor"),
        )
    op.execute("COMMIT")


def downgrade():
    for coluna in _PRODUTO_COLUNAS:
        op.alter_column(
            "sankhya_produtos",
            coluna,
            type_=sa.Float(),
            existing_type=sa.Numeric(15, 2),
        )
    for coluna in _NFE_COLUNAS:
        op.alter_column(
            "sankhya_nfe",
            coluna,
            type_=sa.Float(),
            existing_type=sa.Numeric(15, 2),
        )
    for coluna in _LANCAMENTO_COLUNAS:
        op.alter_column(
            "sankhya_lancamentos_financeiros",
            coluna,
            type_=sa.Float(),
            existing_type=sa.Numeric(15, 2),
            existing_nullable=(coluna != "valor"),
        )
    op.execute("COMMIT")
