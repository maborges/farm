"""adiciona 'PERDA' a ck_estoque_movimentos_origem

OPERATIONS-GAP-01 §21.13: toda perda de estoque (quebra, deterioração, avaria)
era registrada como "AJUSTE" genérico, sem categoria dedicada, impossibilitando
relatório de perdas. `AjusteEstoqueRequest.categoria_ajuste="PERDA"` agora grava
origem="PERDA" em vez de "AJUSTE" — precisa estar na whitelist da constraint.

Revision ID: 20260815_estoque_origem_perda
Revises: 20260815_caderno_lote_rastreab_fk
Create Date: 2026-08-15
"""
from alembic import op

revision = "20260815_estoque_origem_perda"
down_revision = "20260815_caderno_lote_rastreab_fk"
branch_labels = None
depends_on = None

_VALORES = (
    "'OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
    "'TRANSFERENCIA', 'IMPLANTACAO', 'PECUARIA_VACINACAO', 'REQUISICAO', 'LEGADO', 'PERDA'"
)

_VALORES_SEM_PERDA = (
    "'OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
    "'TRANSFERENCIA', 'IMPLANTACAO', 'PECUARIA_VACINACAO', 'REQUISICAO', 'LEGADO'"
)


def upgrade():
    op.execute(
        "ALTER TABLE estoque_movimentos DROP CONSTRAINT IF EXISTS ck_estoque_movimentos_origem"
    )
    op.create_check_constraint(
        "ck_estoque_movimentos_origem",
        "estoque_movimentos",
        f"origem IN ({_VALORES})",
    )
    op.execute("COMMIT")


def downgrade():
    op.execute(
        "ALTER TABLE estoque_movimentos DROP CONSTRAINT IF EXISTS ck_estoque_movimentos_origem"
    )
    op.create_check_constraint(
        "ck_estoque_movimentos_origem",
        "estoque_movimentos",
        f"origem IN ({_VALORES_SEM_PERDA})",
    )
    op.execute("COMMIT")
