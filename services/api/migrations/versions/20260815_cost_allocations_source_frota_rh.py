"""adiciona valores de source gerados por _mapear_source ainda ausentes da constraint

OPERATIONS-GAP-01 §21.14 (achado colateral): nenhum dos 6 valores que
`OperationalCostAllocationService._mapear_source()` (agricola/custos/
operational_cost_service.py) de fato produz para frota/RH estava na whitelist
de `ck_cost_allocations_source` — só não quebrava em produção porque, na
maioria dos casos, o production_unit_id desses fluxos não resolve (o que faz
`_upsert_allocation` retornar None antes do INSERT). Exposto por
tests/test_frota_apontamentos_step08.py ao criar um cenário onde o
production_unit_id resolve de fato.

Revision ID: 20260815_cost_alloc_src_frota_rh
Revises: 20260815_cost_alloc_src_mao_obra
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_cost_alloc_src_frota_rh"
down_revision = "20260815_cost_alloc_src_mao_obra"
branch_labels = None
depends_on = None


def _rebuild_check_constraint(valores: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("cost_allocations")}
    if "ck_cost_allocations_source" in constraints:
        op.drop_constraint("ck_cost_allocations_source", "cost_allocations", type_="check")
    op.create_check_constraint(
        "ck_cost_allocations_source",
        "cost_allocations",
        f"source IN ({valores})",
    )


def upgrade() -> None:
    _rebuild_check_constraint(
        "'OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL','PECUARIA_VACINACAO',"
        "'APONTAMENTO_MAO_OBRA','FROTA_APONTAMENTO','FROTA_COMBUSTIVEL','FROTA_PECAS','FROTA_MANUTENCAO',"
        "'RH_DIARIA','RH_EMPREITADA'"
    )
    op.execute("COMMIT")


def downgrade() -> None:
    _rebuild_check_constraint(
        "'OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL','PECUARIA_VACINACAO','APONTAMENTO_MAO_OBRA'"
    )
    op.execute("COMMIT")
