"""tenant_fk_repair_01c_step2: FKs compostas (tenant_id, parent_id) nos 7 agregados críticos

Revision ID: tenant_fk_repair_01c_step2
Revises: tenant_fk_repair_01c_step1
Create Date: 2026-07-17

Filhos e relações cobertas:
  cadastros_areas_rurais    (tenant_id, unidade_produtiva_id) → unidades_produtivas(tenant_id, id)
  estoque_depositos         (tenant_id, unidade_produtiva_id) → unidades_produtivas(tenant_id, id)
  cadastros_equipamentos    (tenant_id, unidade_produtiva_id) → unidades_produtivas(tenant_id, id)
  compras_pedidos           (tenant_id, deposito_id)          → estoque_depositos(tenant_id, id)
  frota_jornadas_equipamento(tenant_id, unidade_produtiva_id) → unidades_produtivas(tenant_id, id)
  frota_apontamentos_uso    (tenant_id, jornada_id)           → frota_jornadas_equipamento(tenant_id, id)
  frota_abastecimentos      (tenant_id, equipamento_id)       → cadastros_equipamentos(tenant_id, id)

Estratégia:
  - NOT VALID → sem lock, sem scan de linhas existentes
  - VALIDATE  → validação online (ShareUpdateExclusiveLock mínimo)
  - ON DELETE RESTRICT → nunca CASCADE em FK composta de tenant
  - Depende de 01c_step1 (UNIQUE constraints nos pais)
"""
from alembic import op

revision = "tenant_fk_repair_01c_step2"
down_revision = "tenant_fk_repair_01c_step1"
branch_labels = None
depends_on = None


def _add_composite_fk(
    child_table: str,
    child_cols: tuple[str, str],
    parent_table: str,
    parent_cols: tuple[str, str],
    constraint_name: str,
) -> None:
    child_col_str  = ", ".join(child_cols)
    parent_col_str = ", ".join(parent_cols)
    op.execute(f"""
        ALTER TABLE farms.{child_table}
        ADD CONSTRAINT {constraint_name}
        FOREIGN KEY ({child_col_str})
        REFERENCES farms.{parent_table} ({parent_col_str})
        ON DELETE RESTRICT
        NOT VALID
    """)
    op.execute(f"""
        ALTER TABLE farms.{child_table}
        VALIDATE CONSTRAINT {constraint_name}
    """)


def upgrade() -> None:
    # 1. cadastros_areas_rurais → unidades_produtivas
    _add_composite_fk(
        "cadastros_areas_rurais",
        ("tenant_id", "unidade_produtiva_id"),
        "unidades_produtivas",
        ("tenant_id", "id"),
        "fk_car_tenant_unidade_produtiva",
    )

    # 2. estoque_depositos → unidades_produtivas
    _add_composite_fk(
        "estoque_depositos",
        ("tenant_id", "unidade_produtiva_id"),
        "unidades_produtivas",
        ("tenant_id", "id"),
        "fk_ed_tenant_unidade_produtiva",
    )

    # 3. cadastros_equipamentos → unidades_produtivas
    _add_composite_fk(
        "cadastros_equipamentos",
        ("tenant_id", "unidade_produtiva_id"),
        "unidades_produtivas",
        ("tenant_id", "id"),
        "fk_ce_tenant_unidade_produtiva",
    )

    # 4. compras_pedidos → estoque_depositos
    _add_composite_fk(
        "compras_pedidos",
        ("tenant_id", "deposito_id"),
        "estoque_depositos",
        ("tenant_id", "id"),
        "fk_cp_tenant_deposito",
    )

    # 5. frota_jornadas_equipamento → unidades_produtivas
    _add_composite_fk(
        "frota_jornadas_equipamento",
        ("tenant_id", "unidade_produtiva_id"),
        "unidades_produtivas",
        ("tenant_id", "id"),
        "fk_fje_tenant_unidade_produtiva",
    )

    # 6. frota_apontamentos_uso → frota_jornadas_equipamento
    _add_composite_fk(
        "frota_apontamentos_uso",
        ("tenant_id", "jornada_id"),
        "frota_jornadas_equipamento",
        ("tenant_id", "id"),
        "fk_fau_tenant_jornada",
    )

    # 7. frota_abastecimentos → cadastros_equipamentos
    _add_composite_fk(
        "frota_abastecimentos",
        ("tenant_id", "equipamento_id"),
        "cadastros_equipamentos",
        ("tenant_id", "id"),
        "fk_fa_tenant_equipamento",
    )

    op.execute("COMMIT")


def downgrade() -> None:
    constraints = [
        ("cadastros_areas_rurais",     "fk_car_tenant_unidade_produtiva"),
        ("estoque_depositos",           "fk_ed_tenant_unidade_produtiva"),
        ("cadastros_equipamentos",      "fk_ce_tenant_unidade_produtiva"),
        ("compras_pedidos",             "fk_cp_tenant_deposito"),
        ("frota_jornadas_equipamento",  "fk_fje_tenant_unidade_produtiva"),
        ("frota_apontamentos_uso",      "fk_fau_tenant_jornada"),
        ("frota_abastecimentos",        "fk_fa_tenant_equipamento"),
    ]
    for table, name in constraints:
        op.execute(f"""
            ALTER TABLE farms.{table}
            DROP CONSTRAINT IF EXISTS {name}
        """)
    op.execute("COMMIT")
