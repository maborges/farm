"""add_modelos_zoosanitarios

Revision ID: b3e8dc35c257
Revises: fb09b95925e1
Create Date: 2026-08-23 18:11:55.602588

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b3e8dc35c257'
down_revision = 'fb09b95925e1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('modelos_zoosanitarios',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=True),
    sa.Column('especie', sa.String(length=100), nullable=False),
    sa.Column('tipo_risco', sa.String(length=150), nullable=False),
    sa.Column('regras_risco', sa.JSON(), nullable=False),
    sa.Column('is_global', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'especie', 'tipo_risco', name='uq_modelos_zoo_especie_risco')
    )
    with op.batch_alter_table('modelos_zoosanitarios', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_modelos_zoosanitarios_especie'), ['especie'], unique=False)
        batch_op.create_index(batch_op.f('ix_modelos_zoosanitarios_tenant_id'), ['tenant_id'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('modelos_zoosanitarios', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_modelos_zoosanitarios_tenant_id'))
        batch_op.drop_index(batch_op.f('ix_modelos_zoosanitarios_especie'))
    op.drop_table('modelos_zoosanitarios')
