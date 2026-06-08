"""add_lote_comercial_and_publica_foto

Revision ID: a4dc0640fdcf
Revises: 20260607_field_pwa04
Create Date: 2026-06-07 00:37:17.904759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a4dc0640fdcf'
down_revision: Union[str, Sequence[str], None] = '20260607_field_pwa04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criar a tabela caderno_lotes_comerciais
    op.create_table('caderno_lotes_comerciais',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('comercializacao_id', sa.Uuid(), nullable=False),
    sa.Column('produto_colhido_id', sa.Uuid(), nullable=True),
    sa.Column('lote_beneficiamento_id', sa.Uuid(), nullable=True),
    sa.Column('codigo_lote', sa.String(length=100), nullable=False),
    sa.Column('qr_code_token', sa.String(length=64), nullable=False),
    sa.Column('peso_liquido_kg', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('quantidade_volumes', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('snapshot_json', sa.JSON(), nullable=True),
    sa.Column('snapshot_hash', sa.String(length=64), nullable=True),
    sa.Column('snapshot_gerado_em', sa.DateTime(), nullable=True),
    sa.Column('assinado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('assinado_em', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['assinado_por_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['comercializacao_id'], ['financeiro_comercializacoes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['lote_beneficiamento_id'], ['cafe_lotes_beneficiamento.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['produto_colhido_id'], ['agricola_produtos_colhidos.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('caderno_lotes_comerciais', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_caderno_lotes_comerciais_comercializacao_id'), ['comercializacao_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_caderno_lotes_comerciais_lote_beneficiamento_id'), ['lote_beneficiamento_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_caderno_lotes_comerciais_produto_colhido_id'), ['produto_colhido_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_caderno_lotes_comerciais_qr_code_token'), ['qr_code_token'], unique=True)
        batch_op.create_index(batch_op.f('ix_caderno_lotes_comerciais_tenant_id'), ['tenant_id'], unique=False)

    # 2. Adicionar coluna publica na tabela caderno_campo_fotos
    with op.batch_alter_table('caderno_campo_fotos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('publica', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    # 1. Remover coluna publica da tabela caderno_campo_fotos
    with op.batch_alter_table('caderno_campo_fotos', schema=None) as batch_op:
        batch_op.drop_column('publica')

    # 2. Remover tabela caderno_lotes_comerciais
    with op.batch_alter_table('caderno_lotes_comerciais', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_caderno_lotes_comerciais_tenant_id'))
        batch_op.drop_index(batch_op.f('ix_caderno_lotes_comerciais_qr_code_token'))
        batch_op.drop_index(batch_op.f('ix_caderno_lotes_comerciais_produto_colhido_id'))
        batch_op.drop_index(batch_op.f('ix_caderno_lotes_comerciais_lote_beneficiamento_id'))
        batch_op.drop_index(batch_op.f('ix_caderno_lotes_comerciais_comercializacao_id'))
    op.drop_table('caderno_lotes_comerciais')
