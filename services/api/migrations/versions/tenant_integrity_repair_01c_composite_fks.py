"""tenant_integrity_repair_01c: FKs compostas para proteção cross-tenant

Revision ID: tenant_integrity_repair_01c
Revises: 265b28773962
Create Date: 2026-07-17
"""
from alembic import op

revision = "tenant_integrity_repair_01c"
down_revision = "265b28773962"
branch_labels = None
depends_on = ("20260716_config_up_security_freeze",)


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # STEP 1: UNIQUE compostos nos pais
    # unidades_produtivas já tem: uq_unidades_produtivas_tenant_id_id  ✓
    # estoque_depositos: sem UNIQUE(tenant_id, id) — criar
    # frota_jornadas_equipamento: sem UNIQUE(tenant_id, id) — criar
    # cadastros_equipamentos: sem UNIQUE(tenant_id, id) — criar
    # -------------------------------------------------------------------------
    op.execute("""
        ALTER TABLE farms.estoque_depositos
        ADD CONSTRAINT uq_estoque_depositos_tenant_id
        UNIQUE (tenant_id, id)
    """)
    op.execute("""
        ALTER TABLE farms.frota_jornadas_equipamento
        ADD CONSTRAINT uq_frota_jornadas_tenant_id
        UNIQUE (tenant_id, id)
    """)
    op.execute("""
        ALTER TABLE farms.cadastros_equipamentos
        ADD CONSTRAINT uq_cadastros_equipamentos_tenant_id
        UNIQUE (tenant_id, id)
    """)

    # -------------------------------------------------------------------------
    # STEP 2: FKs compostas nos filhos (NOT VALID + VALIDATE para reduzir lock)
    # -------------------------------------------------------------------------

    # 1. cadastros_areas_rurais → unidades_produtivas (NOT NULL, CASCADE)
    op.execute("""
        ALTER TABLE farms.cadastros_areas_rurais
        ADD CONSTRAINT fk_car_tenant_unidade_produtiva
        FOREIGN KEY (tenant_id, unidade_produtiva_id)
        REFERENCES farms.unidades_produtivas (tenant_id, id)
        ON DELETE CASCADE NOT VALID
    """)
    op.execute("""
        ALTER TABLE farms.cadastros_areas_rurais
        VALIDATE CONSTRAINT fk_car_tenant_unidade_produtiva
    """)

    # 2. estoque_depositos → unidades_produtivas (NOT NULL, NO ACTION)
    op.execute("""
        ALTER TABLE farms.estoque_depositos
        ADD CONSTRAINT fk_ed_tenant_unidade_produtiva
        FOREIGN KEY (tenant_id, unidade_produtiva_id)
        REFERENCES farms.unidades_produtivas (tenant_id, id)
        ON DELETE NO ACTION NOT VALID
    """)
    op.execute("""
        ALTER TABLE farms.estoque_depositos
        VALIDATE CONSTRAINT fk_ed_tenant_unidade_produtiva
    """)

    # 3. cadastros_equipamentos → unidades_produtivas (NULLABLE, SET NULL não suportado em FK composta — usar NO ACTION)
    op.execute("""
        ALTER TABLE farms.cadastros_equipamentos
        ADD CONSTRAINT fk_ce_tenant_unidade_produtiva
        FOREIGN KEY (tenant_id, unidade_produtiva_id)
        REFERENCES farms.unidades_produtivas (tenant_id, id)
        ON DELETE NO ACTION NOT VALID
    """)
    op.execute("""
        ALTER TABLE farms.cadastros_equipamentos
        VALIDATE CONSTRAINT fk_ce_tenant_unidade_produtiva
    """)

    # 4. compras_pedidos → estoque_depositos (NULLABLE, NO ACTION)
    op.execute("""
        ALTER TABLE farms.compras_pedidos
        ADD CONSTRAINT fk_cp_tenant_deposito
        FOREIGN KEY (tenant_id, deposito_id)
        REFERENCES farms.estoque_depositos (tenant_id, id)
        ON DELETE NO ACTION NOT VALID
    """)
    op.execute("""
        ALTER TABLE farms.compras_pedidos
        VALIDATE CONSTRAINT fk_cp_tenant_deposito
    """)

    # 5. frota_jornadas_equipamento → unidades_produtivas (NULLABLE, SET NULL → NO ACTION)
    op.execute("""
        ALTER TABLE farms.frota_jornadas_equipamento
        ADD CONSTRAINT fk_fje_tenant_unidade_produtiva
        FOREIGN KEY (tenant_id, unidade_produtiva_id)
        REFERENCES farms.unidades_produtivas (tenant_id, id)
        ON DELETE NO ACTION NOT VALID
    """)
    op.execute("""
        ALTER TABLE farms.frota_jornadas_equipamento
        VALIDATE CONSTRAINT fk_fje_tenant_unidade_produtiva
    """)

    # 6. frota_apontamentos_uso → frota_jornadas_equipamento (NULLABLE, SET NULL → NO ACTION)
    op.execute("""
        ALTER TABLE farms.frota_apontamentos_uso
        ADD CONSTRAINT fk_fau_tenant_jornada
        FOREIGN KEY (tenant_id, jornada_id)
        REFERENCES farms.frota_jornadas_equipamento (tenant_id, id)
        ON DELETE NO ACTION NOT VALID
    """)
    op.execute("""
        ALTER TABLE farms.frota_apontamentos_uso
        VALIDATE CONSTRAINT fk_fau_tenant_jornada
    """)

    # 7. frota_abastecimentos → cadastros_equipamentos (NOT NULL, CASCADE)
    op.execute("""
        ALTER TABLE farms.frota_abastecimentos
        ADD CONSTRAINT fk_fa_tenant_equipamento
        FOREIGN KEY (tenant_id, equipamento_id)
        REFERENCES farms.cadastros_equipamentos (tenant_id, id)
        ON DELETE CASCADE NOT VALID
    """)
    op.execute("""
        ALTER TABLE farms.frota_abastecimentos
        VALIDATE CONSTRAINT fk_fa_tenant_equipamento
    """)

    op.execute("COMMIT")


def downgrade() -> None:
    # Remover FKs compostas
    op.execute("ALTER TABLE farms.frota_abastecimentos DROP CONSTRAINT IF EXISTS fk_fa_tenant_equipamento")
    op.execute("ALTER TABLE farms.frota_apontamentos_uso DROP CONSTRAINT IF EXISTS fk_fau_tenant_jornada")
    op.execute("ALTER TABLE farms.frota_jornadas_equipamento DROP CONSTRAINT IF EXISTS fk_fje_tenant_unidade_produtiva")
    op.execute("ALTER TABLE farms.compras_pedidos DROP CONSTRAINT IF EXISTS fk_cp_tenant_deposito")
    op.execute("ALTER TABLE farms.cadastros_equipamentos DROP CONSTRAINT IF EXISTS fk_ce_tenant_unidade_produtiva")
    op.execute("ALTER TABLE farms.estoque_depositos DROP CONSTRAINT IF EXISTS fk_ed_tenant_unidade_produtiva")
    op.execute("ALTER TABLE farms.cadastros_areas_rurais DROP CONSTRAINT IF EXISTS fk_car_tenant_unidade_produtiva")
    # Remover UNIQUE compostos nos pais
    op.execute("ALTER TABLE farms.cadastros_equipamentos DROP CONSTRAINT IF EXISTS uq_cadastros_equipamentos_tenant_id")
    op.execute("ALTER TABLE farms.frota_jornadas_equipamento DROP CONSTRAINT IF EXISTS uq_frota_jornadas_tenant_id")
    op.execute("ALTER TABLE farms.estoque_depositos DROP CONSTRAINT IF EXISTS uq_estoque_depositos_tenant_id")
    op.execute("COMMIT")
