"""add pin_hash em campo_dispositivos

Revision ID: 20260803_disp_pin_hash
Revises: 20260803_req_confirmacoes
Create Date: 2026-08-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260803_disp_pin_hash'
down_revision: Union[str, Sequence[str], None] = '20260803_req_confirmacoes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'campo_dispositivos',
        sa.Column('pin_hash', sa.String(255), nullable=True),
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_column('campo_dispositivos', 'pin_hash')
    op.execute("COMMIT")
