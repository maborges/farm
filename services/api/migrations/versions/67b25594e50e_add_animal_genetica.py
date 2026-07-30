"""add animal_genetica

Revision ID: 67b25594e50e
Revises: 20260729_ordens_pagamento
Create Date: 2026-07-30 01:30:03.952967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67b25594e50e'
down_revision: Union[str, Sequence[str], None] = '20260729_ordens_pagamento'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # racas
    op.create_table('racas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('especie', sa.String(length=50), nullable=True),
        sa.Column('origem', sa.String(length=100), nullable=True),
        sa.Column('peso_adulto_macho', sa.Float(), nullable=True),
        sa.Column('peso_adulto_femea', sa.Float(), nullable=True),
        sa.Column('cor_padrao', sa.String(length=50), nullable=True),
        sa.Column('dep_ganho_peso', sa.Float(), nullable=True),
        sa.Column('dep_area_olho_lombo', sa.Float(), nullable=True),
        sa.Column('dep_gordura_subcutanea', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_racas_id'), 'racas', ['id'], unique=False)

    # animal_genetica
    op.create_table('animal_genetica',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('animal_id', sa.Integer(), nullable=True),
        sa.Column('brinco', sa.String(length=50), nullable=True),
        sa.Column('raca_id', sa.Integer(), sa.ForeignKey('racas.id'), nullable=True),
        sa.Column('pai_id', sa.Integer(), nullable=True),
        sa.Column('mae_id', sa.Integer(), nullable=True),
        sa.Column('dep_ganho_peso', sa.Float(), nullable=True),
        sa.Column('dep_area_olho_lombo', sa.Float(), nullable=True),
        sa.Column('dep_gordura_subcutanea', sa.Float(), nullable=True),
        sa.Column('dep_maciez', sa.Float(), nullable=True),
        sa.Column('matriz', sa.Boolean(), nullable=True),
        sa.Column('reprodutor', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_animal_genetica_id'), 'animal_genetica', ['id'], unique=False)

    # sugestoes_acasalamento
    op.create_table('sugestoes_acasalamento',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('matriz_id', sa.Integer(), nullable=False),
        sa.Column('reprodutor_id', sa.Integer(), nullable=False),
        sa.Column('dep_esperado', sa.JSON(), nullable=True),
        sa.Column('score_complementaridade', sa.Float(), nullable=True),
        sa.Column('realizado', sa.Boolean(), nullable=True),
        sa.Column('data_acasalamento', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sugestoes_acasalamento_id'), 'sugestoes_acasalamento', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_sugestoes_acasalamento_id'), table_name='sugestoes_acasalamento')
    op.drop_table('sugestoes_acasalamento')
    op.drop_index(op.f('ix_animal_genetica_id'), table_name='animal_genetica')
    op.drop_table('animal_genetica')
    op.drop_index(op.f('ix_racas_id'), table_name='racas')
    op.drop_table('racas')
