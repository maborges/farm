"""permite REQUISICAO na constraint de origem de estoque_movimentos

Revision ID: 20260803_mov_origem_req
Revises: 20260803_req_op_agricola
Create Date: 2026-08-03

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260803_mov_origem_req'
down_revision: Union[str, Sequence[str], None] = '20260803_req_op_agricola'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('ck_estoque_movimentos_origem', 'estoque_movimentos', type_='check')
    op.create_check_constraint(
        'ck_estoque_movimentos_origem',
        'estoque_movimentos',
        "origem IN ('OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
        "'TRANSFERENCIA', 'IMPLANTACAO', 'PECUARIA_VACINACAO', 'REQUISICAO')",
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_constraint('ck_estoque_movimentos_origem', 'estoque_movimentos', type_='check')
    op.create_check_constraint(
        'ck_estoque_movimentos_origem',
        'estoque_movimentos',
        "origem IN ('OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
        "'TRANSFERENCIA', 'IMPLANTACAO')",
    )
    op.execute("COMMIT")
