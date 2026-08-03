"""add tarefa_campo_id em romaneios_colheita

Revision ID: 20260802_romaneio_tarefa_campo
Revises: 20260802_tarefas_ordem
Create Date: 2026-08-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260802_romaneio_tarefa_campo'
down_revision: Union[str, Sequence[str], None] = '20260802_tarefas_ordem'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'romaneios_colheita',
        sa.Column('tarefa_campo_id', sa.Uuid(), nullable=True),
    )
    op.create_index(
        'ix_romaneios_colheita_tarefa_campo_id',
        'romaneios_colheita',
        ['tarefa_campo_id'],
    )
    op.create_foreign_key(
        'fk_romaneios_colheita_tarefa_campo_id',
        'romaneios_colheita',
        'campo_tarefas',
        ['tarefa_campo_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_constraint('fk_romaneios_colheita_tarefa_campo_id', 'romaneios_colheita', type_='foreignkey')
    op.drop_index('ix_romaneios_colheita_tarefa_campo_id', table_name='romaneios_colheita')
    op.drop_column('romaneios_colheita', 'tarefa_campo_id')
    op.execute("COMMIT")
