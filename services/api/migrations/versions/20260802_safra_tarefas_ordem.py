"""add ordem em safra_tarefas

Revision ID: 20260802_tarefas_ordem
Revises: 20260801_plano_nec_fk
Create Date: 2026-08-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260802_tarefas_ordem'
down_revision: Union[str, Sequence[str], None] = '20260801_plano_nec_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'safra_tarefas',
        sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_column('safra_tarefas', 'ordem')
    op.execute("COMMIT")
