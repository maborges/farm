"""add_capex_viabilidade_planos_acao

Revision ID: 20261118_plano_acao_capex
Revises: 20261116_planos_acao_maturidade
Create Date: 2026-11-18 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20261118_plano_acao_capex"
down_revision = "20261116_planos_acao_maturidade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("planos_acao_gerenciais", sa.Column("investimento_estimado", sa.Float(), nullable=True))
    op.add_column("planos_acao_gerenciais", sa.Column("retorno_anual_estimado", sa.Float(), nullable=True))
    op.add_column("planos_acao_gerenciais", sa.Column("horizonte_anos", sa.Integer(), nullable=True))
    op.add_column("planos_acao_gerenciais", sa.Column("tma_aa", sa.Float(), nullable=True))
    op.add_column("planos_acao_gerenciais", sa.Column("prazo_maximo_payback_anos", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("planos_acao_gerenciais", "prazo_maximo_payback_anos")
    op.drop_column("planos_acao_gerenciais", "tma_aa")
    op.drop_column("planos_acao_gerenciais", "horizonte_anos")
    op.drop_column("planos_acao_gerenciais", "retorno_anual_estimado")
    op.drop_column("planos_acao_gerenciais", "investimento_estimado")
