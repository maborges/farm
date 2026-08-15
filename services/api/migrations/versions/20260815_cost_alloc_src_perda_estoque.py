"""adiciona PERDA_ESTOQUE à whitelist de source em cost_allocations

OPERATIONS-GAP-01 (risco residual #4): perda de estoque (categoria_ajuste=
"PERDA" em AjusteEstoqueRequest) passa a poder gerar CostAllocation quando
vinculável a um ProductionUnit (safra_id+talhao_id informados), fechando o
gap de perdas físicas invisíveis no DRE. Ver
operacional/services/estoque_service.py::registrar_ajuste.

Revision ID: 20260815_cost_alloc_src_perda_estoque
Revises: 20260815_beneficiamento_generico
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_cost_alloc_src_perda_estoque"
down_revision = "20260815_beneficiamento_generico"
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
        "'RH_DIARIA','RH_EMPREITADA','PERDA_ESTOQUE'"
    )
    op.execute("COMMIT")


def downgrade() -> None:
    _rebuild_check_constraint(
        "'OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL','PECUARIA_VACINACAO',"
        "'APONTAMENTO_MAO_OBRA','FROTA_APONTAMENTO','FROTA_COMBUSTIVEL','FROTA_PECAS','FROTA_MANUTENCAO',"
        "'RH_DIARIA','RH_EMPREITADA'"
    )
    op.execute("COMMIT")
