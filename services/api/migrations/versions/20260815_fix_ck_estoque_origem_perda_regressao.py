"""corrige regressão: ck_estoque_movimentos_origem perdeu PERDA/PECUARIA_VACINACAO/REQUISICAO/LEGADO

Bug real descoberto durante o trabalho do risco residual #4 (OPERATIONS-GAP-01):
`20260815_fix_ck_estoque_movimentos_origem.py` foi escrita como "fonte
autoritativa" da constraint (Seção 21.5), mas seu `_VALORES` esqueceu de
incluir `'PERDA'` — que já existia antes, adicionado por
`20260815_estoque_movimentos_origem_perda.py` (Seção 21.13) numa branch
paralela da árvore de migrations. Quando as branches convergiram, a migration
"fix" rodou depois e recriou a constraint sem `'PERDA'`, regredindo
silenciosamente a categorização de perdas de estoque (INSERTs com
origem='PERDA' voltaram a ser rejeitados pelo banco). Confirmado via
`pg_get_constraintdef` que a constraint viva no banco não tinha nenhum dos
quatro valores. Esta migration é a nova fonte autoritativa, reunindo todos os
valores usados em código ativo.

Revision ID: 20260815_fix_ck_estoque_origem_perda_regressao
Revises: 20260815_cost_alloc_src_perda_estoque
Create Date: 2026-08-15
"""
from alembic import op

revision = "20260815_fix_ck_estoque_origem_perda_regressao"
down_revision = "20260815_cost_alloc_src_perda_estoque"
branch_labels = None
depends_on = None

_VALORES = (
    "'OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
    "'TRANSFERENCIA', 'IMPLANTACAO', 'PECUARIA_VACINACAO', 'REQUISICAO', "
    "'LEGADO', 'PERDA'"
)

_VALORES_ANTERIORES = (
    "'OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
    "'TRANSFERENCIA', 'IMPLANTACAO'"
)


def upgrade() -> None:
    op.execute("ALTER TABLE estoque_movimentos DROP CONSTRAINT IF EXISTS ck_estoque_movimentos_origem")
    op.create_check_constraint(
        "ck_estoque_movimentos_origem",
        "estoque_movimentos",
        f"origem IN ({_VALORES})",
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.execute("ALTER TABLE estoque_movimentos DROP CONSTRAINT IF EXISTS ck_estoque_movimentos_origem")
    op.create_check_constraint(
        "ck_estoque_movimentos_origem",
        "estoque_movimentos",
        f"origem IN ({_VALORES_ANTERIORES})",
    )
    op.execute("COMMIT")
