"""add confinamento models

Revision ID: 67b25594e50f
Revises: 67b25594e50e
Create Date: 2026-07-30 01:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '67b25594e50f'
down_revision: Union[str, Sequence[str], None] = '67b25594e50e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # confinamento_lotes
    op.create_table('confinamento_lotes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('unidade_produtiva_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('unidades_produtivas.id'), nullable=True),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('safra', sa.String(length=20), nullable=True),
        sa.Column('total_animais', sa.Integer(), nullable=True),
        sa.Column('peso_inicial_kg', sa.Float(), nullable=True),
        sa.Column('peso_inicial_total_kg', sa.Float(), nullable=True),
        sa.Column('data_entrada', sa.Date(), nullable=False),
        sa.Column('data_saida_prevista', sa.Date(), nullable=True),
        sa.Column('data_saida_real', sa.Date(), nullable=True),
        sa.Column('peso_saida_kg', sa.Float(), nullable=True),
        sa.Column('ganho_medio_diario', sa.Float(), nullable=True),
        sa.Column('conversao_alimentar', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='confinado'),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_confinamento_lotes_id'), 'confinamento_lotes', ['id'], unique=False)

    # racoes_tmr
    op.create_table('racoes_tmr',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=True),
        sa.Column('ingredientes', sa.JSON(), nullable=True),
        sa.Column('proteina_bruta', sa.Float(), nullable=True),
        sa.Column('ndt', sa.Float(), nullable=True),
        sa.Column('energia_liquida', sa.Float(), nullable=True),
        sa.Column('custo_por_tonelada', sa.Float(), nullable=True),
        sa.Column('ativa', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_racoes_tmr_id'), 'racoes_tmr', ['id'], unique=False)

    # cochos
    op.create_table('cochos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('lote_id', sa.Integer(), sa.ForeignKey('confinamento_lotes.id'), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('comprimento_m', sa.Float(), nullable=True),
        sa.Column('racao_fornecida_kg', sa.Float(), nullable=True),
        sa.Column('sobra_kg', sa.Float(), nullable=True),
        sa.Column('consumo_kg', sa.Float(), nullable=True),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('turno', sa.String(length=20), nullable=True),
        sa.Column('responsavel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cochos_id'), 'cochos', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_cochos_id'), table_name='cochos')
    op.drop_table('cochos')
    op.drop_index(op.f('ix_racoes_tmr_id'), table_name='racoes_tmr')
    op.drop_table('racoes_tmr')
    op.drop_index(op.f('ix_confinamento_lotes_id'), table_name='confinamento_lotes')
    op.drop_table('confinamento_lotes')
