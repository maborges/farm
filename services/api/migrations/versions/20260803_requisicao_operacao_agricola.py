"""add operacao_agricola_id em estoque_requisicoes

Revision ID: 20260803_req_op_agricola
Revises: 20260802_romaneio_tarefa_campo
Create Date: 2026-08-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260803_req_op_agricola'
down_revision: Union[str, Sequence[str], None] = '20260802_romaneio_tarefa_campo'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'estoque_requisicoes',
        sa.Column('operacao_agricola_id', sa.Uuid(), nullable=True),
    )
    op.create_index(
        'ix_estoque_requisicoes_operacao_agricola_id',
        'estoque_requisicoes',
        ['operacao_agricola_id'],
    )
    op.create_foreign_key(
        'fk_estoque_requisicoes_operacao_agricola_id',
        'estoque_requisicoes',
        'operacoes_agricolas',
        ['operacao_agricola_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_constraint('fk_estoque_requisicoes_operacao_agricola_id', 'estoque_requisicoes', type_='foreignkey')
    op.drop_index('ix_estoque_requisicoes_operacao_agricola_id', table_name='estoque_requisicoes')
    op.drop_column('estoque_requisicoes', 'operacao_agricola_id')
    op.execute("COMMIT")
