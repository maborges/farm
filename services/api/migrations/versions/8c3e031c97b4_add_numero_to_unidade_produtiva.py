"""add_numero_to_unidade_produtiva

Revision ID: 8c3e031c97b4
Revises: 20260712_integrations_tenant_integracao_unique_indexes
Create Date: 2026-07-13 16:47:01.911016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c3e031c97b4'
down_revision: Union[str, Sequence[str], None] = '20260712_integrations_tenant_integracao_unique_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('unidades_produtivas', sa.Column('numero', sa.String(length=20), nullable=True, comment='Número do endereço'))


def downgrade() -> None:
    op.drop_column('unidades_produtivas', 'numero')
