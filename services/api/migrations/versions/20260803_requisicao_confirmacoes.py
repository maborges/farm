"""add estoque_requisicao_confirmacoes e quantidade_devolvida

Revision ID: 20260803_req_confirmacoes
Revises: 20260803_mov_origem_req
Create Date: 2026-08-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260803_req_confirmacoes'
down_revision: Union[str, Sequence[str], None] = '20260803_mov_origem_req'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'estoque_requisicoes_itens',
        sa.Column('quantidade_devolvida', sa.Float(), nullable=True),
    )

    op.create_table(
        'estoque_requisicao_confirmacoes',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('tenant_id', sa.Uuid(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('requisicao_id', sa.Uuid(), sa.ForeignKey('estoque_requisicoes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('usuario_id', sa.Uuid(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('metodo', sa.String(20), nullable=False),
        sa.Column('email_informado', sa.String(255), nullable=True),
        sa.Column('confirmado_em', sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_table('estoque_requisicao_confirmacoes')
    op.drop_column('estoque_requisicoes_itens', 'quantidade_devolvida')
    op.execute("COMMIT")
