"""corrige ck_estoque_movimentos_origem: une valores divergentes de duas migrations anteriores

Duas correções divergentes desta constraint coexistiam na árvore de migrations
(step24_estoque_movimentos_origem_legado.py, adicionando 'LEGADO', e
20260803_estoque_mov_origem_requisicao.py, adicionando 'PECUARIA_VACINACAO' e
'REQUISICAO') e o estado real do banco não refletia nenhuma das duas por completo,
quebrando a materialização de vacinação em estoque (EstoqueMovimento.origem =
'PECUARIA_VACINACAO' rejeitado pela constraint). Esta migration é a fonte
autoritativa: recria a constraint com a união de todos os valores usados em código
ativo (`operacional/models/estoque.py`, `pecuaria/services/manejo_sync_service.py`,
`operacional/services/estoque_service.py`), de forma idempotente.

Revision ID: 20260815_fix_ck_estoque_origem
Revises: 20260815_estoque_numeric
Create Date: 2026-08-15
"""
from alembic import op

revision = "20260815_fix_ck_estoque_origem"
down_revision = "20260815_estoque_numeric"
branch_labels = None
depends_on = None

_VALORES = (
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
        "origem IN ('OPERACAO_EXECUCAO', 'COMPRA', 'COLHEITA', 'AJUSTE', 'MANUAL', "
        "'TRANSFERENCIA', 'IMPLANTACAO')",
    )
    op.execute("COMMIT")
