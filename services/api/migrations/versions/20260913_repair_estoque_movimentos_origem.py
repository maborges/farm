"""repair inventory movement origin whitelist in the live operational schema.

The integration database is stamped at the operational head but still has the
old seven-value CHECK constraint. Rebuild it from the complete set currently
emitted by active services, including legacy and loss movements.
"""

from alembic import op


revision = "20260913_repair_estoque_movimentos_origem"
down_revision = "20260828_balanca_webhook_credentials"
branch_labels = None
depends_on = None


_VALUES = (
    "'OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
    "'TRANSFERENCIA', 'IMPLANTACAO', 'PECUARIA_VACINACAO', 'REQUISICAO', "
    "'LEGADO', 'PERDA'"
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE farms.estoque_movimentos "
        "DROP CONSTRAINT IF EXISTS ck_estoque_movimentos_origem"
    )
    op.execute(
        "ALTER TABLE farms.estoque_movimentos ADD CONSTRAINT "
        "ck_estoque_movimentos_origem CHECK (origem IN ("
        f"{_VALUES}" ")) NOT VALID"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE farms.estoque_movimentos "
        "DROP CONSTRAINT IF EXISTS ck_estoque_movimentos_origem"
    )
    op.execute(
        "ALTER TABLE farms.estoque_movimentos ADD CONSTRAINT "
        "ck_estoque_movimentos_origem CHECK (origem IN ("
        "'OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
        "'TRANSFERENCIA', 'IMPLANTACAO'" ")) NOT VALID"
    )
