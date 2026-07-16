"""territory_convergence_remove_legacy_columns

Revision ID: 265b28773962
Revises: 5cee1dab62fb
Create Date: 2026-07-16 10:33:44.636157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '265b28773962'
down_revision: Union[str, Sequence[str], None] = '5cee1dab62fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criar tabela de preservação
    op.execute("""
        CREATE TABLE IF NOT EXISTS farms.territory_legacy_backup_01h2 (
            id SERIAL PRIMARY KEY,
            tenant_id UUID,
            unidade_produtiva_id UUID,
            imovel_rural_id UUID,
            nirf VARCHAR(20),
            codigo_car VARCHAR(80),
            ccir VARCHAR(30),
            sigef_codigo VARCHAR(50),
            numero_matricula VARCHAR(100),
            legacy_imovel_unidade_produtiva_id UUID,
            backup_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            migration_revision VARCHAR(50) DEFAULT '265b28773962'
        )
    """)

    # 2. Copiar os valores legados
    op.execute("""
        INSERT INTO farms.territory_legacy_backup_01h2 (
            tenant_id, unidade_produtiva_id, nirf, codigo_car, ccir, sigef_codigo, numero_matricula
        )
        SELECT tenant_id, id, nirf, codigo_car, ccir, sigef_codigo, numero_matricula
        FROM farms.unidades_produtivas
        WHERE nirf IS NOT NULL OR codigo_car IS NOT NULL OR ccir IS NOT NULL OR sigef_codigo IS NOT NULL OR numero_matricula IS NOT NULL
    """)
    
    op.execute("""
        INSERT INTO farms.territory_legacy_backup_01h2 (
            tenant_id, imovel_rural_id, legacy_imovel_unidade_produtiva_id
        )
        SELECT tenant_id, id, unidade_produtiva_id
        FROM farms.imoveis_rurais
        WHERE unidade_produtiva_id IS NOT NULL
    """)

    # 4. Remover colunas de imoveis_rurais
    op.drop_column('imoveis_rurais', 'unidade_produtiva_id', schema='farms')

    # 5. Remover colunas de unidades_produtivas
    op.drop_column('unidades_produtivas', 'nirf', schema='farms')
    op.drop_column('unidades_produtivas', 'codigo_car', schema='farms')
    op.drop_column('unidades_produtivas', 'ccir', schema='farms')
    op.drop_column('unidades_produtivas', 'sigef_codigo', schema='farms')
    op.drop_column('unidades_produtivas', 'numero_matricula', schema='farms')


def downgrade() -> None:
    # 1. Recriar as colunas
    op.add_column('unidades_produtivas', sa.Column('nirf', sa.VARCHAR(length=20), autoincrement=False, nullable=True), schema='farms')
    op.add_column('unidades_produtivas', sa.Column('codigo_car', sa.VARCHAR(length=80), autoincrement=False, nullable=True), schema='farms')
    op.add_column('unidades_produtivas', sa.Column('ccir', sa.VARCHAR(length=30), autoincrement=False, nullable=True), schema='farms')
    op.add_column('unidades_produtivas', sa.Column('sigef_codigo', sa.VARCHAR(length=50), autoincrement=False, nullable=True), schema='farms')
    op.add_column('unidades_produtivas', sa.Column('numero_matricula', sa.VARCHAR(length=100), autoincrement=False, nullable=True), schema='farms')
    
    op.add_column('imoveis_rurais', sa.Column('unidade_produtiva_id', sa.UUID(), autoincrement=False, nullable=True), schema='farms')

    # 2. Restaurar dados
    op.execute("""
        UPDATE farms.unidades_produtivas up
        SET nirf = b.nirf,
            codigo_car = b.codigo_car,
            ccir = b.ccir,
            sigef_codigo = b.sigef_codigo,
            numero_matricula = b.numero_matricula
        FROM farms.territory_legacy_backup_01h2 b
        WHERE up.id = b.unidade_produtiva_id
    """)

    op.execute("""
        UPDATE farms.imoveis_rurais ir
        SET unidade_produtiva_id = b.legacy_imovel_unidade_produtiva_id
        FROM farms.territory_legacy_backup_01h2 b
        WHERE ir.id = b.imovel_rural_id
    """)

    # 3. Recriar Constraints / Indexes
    op.create_index('ix_farms_imoveis_rurais_unidade_produtiva_id', 'imoveis_rurais', ['unidade_produtiva_id'], unique=False, schema='farms')
    op.create_foreign_key('imoveis_rurais_unidade_produtiva_id_fkey', 'imoveis_rurais', 'unidades_produtivas', ['unidade_produtiva_id'], ['id'], source_schema='farms', referent_schema='farms', ondelete='RESTRICT')

