"""tenant_fk_repair_01c_step1: UNIQUE(tenant_id, id) nos pais dos 7 agregados críticos

Revision ID: tenant_fk_repair_01c_step1
Revises: tenant_fk_repair_01b
Create Date: 2026-07-17

Pais cobertos:
  - unidades_produtivas        (filho: cadastros_areas_rurais, estoque_depositos,
                                        cadastros_equipamentos, frota_jornadas_equipamento)
  - estoque_depositos          (filho: compras_pedidos)
  - cadastros_equipamentos     (filho: frota_abastecimentos)
  - frota_jornadas_equipamento (filho: frota_apontamentos_uso)

Estratégia:
  - UNIQUE CONCURRENTLY → sem lock de tabela em produção
  - Separado do step2 (FKs compostas) para permitir rollback granular
  - PRÉ-CONDIÇÃO: 01c_diagnose_pre_composite.sql retorna 0 em tudo

ATENÇÃO: CONCURRENTLY não pode rodar dentro de transação.
Esta migration usa op.execute() fora de transação (alembic.ini: transaction_per_migration=false)
ou pode ser executada manualmente via psql.
"""
from alembic import op

revision = "tenant_fk_repair_01c_step1"
down_revision = "tenant_fk_repair_01b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CONCURRENTLY não aceita transação explícita — executar via psql se necessário:
    # CREATE UNIQUE INDEX CONCURRENTLY ...

    # unidades_produtivas
    op.execute("""
        CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
        uq_unidades_produtivas_tenant_id
        ON farms.unidades_produtivas (tenant_id, id)
    """)

    # estoque_depositos
    op.execute("""
        CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
        uq_estoque_depositos_tenant_id
        ON farms.estoque_depositos (tenant_id, id)
    """)

    # cadastros_equipamentos
    op.execute("""
        CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
        uq_cadastros_equipamentos_tenant_id
        ON farms.cadastros_equipamentos (tenant_id, id)
    """)

    # frota_jornadas_equipamento
    op.execute("""
        CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
        uq_frota_jornadas_equipamento_tenant_id
        ON farms.frota_jornadas_equipamento (tenant_id, id)
    """)

    # Promover índices para UNIQUE constraints (necessário para FK referenciar)
    op.execute("""
        ALTER TABLE farms.unidades_produtivas
        ADD CONSTRAINT uq_unidades_produtivas_tenant_id
        UNIQUE USING INDEX uq_unidades_produtivas_tenant_id
    """)
    op.execute("""
        ALTER TABLE farms.estoque_depositos
        ADD CONSTRAINT uq_estoque_depositos_tenant_id
        UNIQUE USING INDEX uq_estoque_depositos_tenant_id
    """)
    op.execute("""
        ALTER TABLE farms.cadastros_equipamentos
        ADD CONSTRAINT uq_cadastros_equipamentos_tenant_id
        UNIQUE USING INDEX uq_cadastros_equipamentos_tenant_id
    """)
    op.execute("""
        ALTER TABLE farms.frota_jornadas_equipamento
        ADD CONSTRAINT uq_frota_jornadas_equipamento_tenant_id
        UNIQUE USING INDEX uq_frota_jornadas_equipamento_tenant_id
    """)

    op.execute("COMMIT")


def downgrade() -> None:
    for table, name in [
        ("unidades_produtivas",        "uq_unidades_produtivas_tenant_id"),
        ("estoque_depositos",           "uq_estoque_depositos_tenant_id"),
        ("cadastros_equipamentos",      "uq_cadastros_equipamentos_tenant_id"),
        ("frota_jornadas_equipamento",  "uq_frota_jornadas_equipamento_tenant_id"),
    ]:
        op.execute(f"""
            ALTER TABLE farms.{table} DROP CONSTRAINT IF EXISTS {name}
        """)
    op.execute("COMMIT")
