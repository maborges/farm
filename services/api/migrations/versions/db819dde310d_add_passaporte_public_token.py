"""add_passaporte_public_token

Revision ID: db819dde310d
Revises: 20260621_certificacao_esg_relatorio_passaporte
Create Date: 2026-06-21 18:14:22.456808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'db819dde310d'
down_revision: Union[str, Sequence[str], None] = '20260621_certificacao_esg_relatorio_passaporte'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('rastreabilidade_passaportes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('public_token', sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column('publicado_publicamente_em', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f('ix_rastreabilidade_passaportes_public_token'), ['public_token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('rastreabilidade_passaportes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rastreabilidade_passaportes_public_token'))
        batch_op.drop_column('publicado_publicamente_em')
        batch_op.drop_column('public_token')
