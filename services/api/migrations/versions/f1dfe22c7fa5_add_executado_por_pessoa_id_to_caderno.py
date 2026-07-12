"""add executado_por_pessoa_id to caderno

Revision ID: f1dfe22c7fa5
Revises: 20260709_sankhya_legacy_gateway_login
Create Date: 2026-07-12 00:05:19.850830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1dfe22c7fa5'
down_revision: Union[str, Sequence[str], None] = '20260709_sankhya_legacy_gateway_login'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('caderno_campo_entradas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('executado_por_pessoa_id', sa.Uuid(), nullable=True))
        batch_op.create_index(batch_op.f('ix_caderno_campo_entradas_executado_por_pessoa_id'), ['executado_por_pessoa_id'], unique=False)
        batch_op.create_foreign_key('fk_caderno_executado_por', 'cadastros_pessoas', ['executado_por_pessoa_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('caderno_campo_entradas', schema=None) as batch_op:
        batch_op.drop_constraint('fk_caderno_executado_por', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_caderno_campo_entradas_executado_por_pessoa_id'))
        batch_op.drop_column('executado_por_pessoa_id')
