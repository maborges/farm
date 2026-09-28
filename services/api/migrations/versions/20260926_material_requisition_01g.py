"""MATERIAL-REQUISITION-FLOW-01G: custo real por consumo canônico.

Adiciona somente o vínculo idempotente entre um evento CONSUMO e seu
CostAllocation. Nenhum fato histórico é recalculado.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_material_requisition_01g"
down_revision: str | Sequence[str] | None = "20260925_material_requisition_01e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SOURCE_VALUES = (
    "OPERATION_EXECUTION",
    "INVENTORY_MOVEMENT",
    "REQUISICAO_CONSUMO",
    "FIN_RATEIO",
    "MANUAL",
    "PECUARIA_VACINACAO",
    "APONTAMENTO_MAO_OBRA",
    "FROTA_APONTAMENTO",
    "FROTA_COMBUSTIVEL",
    "FROTA_PECAS",
    "FROTA_MANUTENCAO",
    "RH_DIARIA",
    "RH_EMPREITADA",
    "PERDA_ESTOQUE",
    "DEPRECIACAO_EQUIPAMENTO",
    "DEPRECIACAO_BENFEITORIA",
)


def _source_check() -> str:
    values = ", ".join(f"'{value}'" for value in SOURCE_VALUES)
    return f"source IN ({values})"


def upgrade() -> None:
    op.add_column(
        "cost_allocations",
        sa.Column("requisicao_item_evento_id", sa.Uuid(), nullable=True),
        schema="farms",
    )
    op.create_foreign_key(
        "fk_cost_allocations_tenant_req_item_evento",
        "cost_allocations",
        "estoque_requisicao_item_eventos",
        ["tenant_id", "requisicao_item_evento_id"],
        ["tenant_id", "id"],
        source_schema="farms",
        referent_schema="farms",
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_cost_allocations_tenant_req_item_evento",
        "cost_allocations",
        ["tenant_id", "requisicao_item_evento_id"],
        schema="farms",
    )
    # Instalações anteriores não possuíam necessariamente esta constraint.
    # Use DDL idempotente para que o contrato novo possa ser aplicado tanto
    # sobre esses bancos quanto sobre os que já trazem a versão anterior.
    op.execute(
        "ALTER TABLE farms.cost_allocations "
        "DROP CONSTRAINT IF EXISTS ck_cost_allocations_source"
    )
    op.create_check_constraint(
        "ck_cost_allocations_source",
        "cost_allocations",
        _source_check(),
        schema="farms",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_cost_allocations_source",
        "cost_allocations",
        type_="check",
        schema="farms",
    )
    op.create_check_constraint(
        "ck_cost_allocations_source",
        "cost_allocations",
        _source_check().replace("'REQUISICAO_CONSUMO', ", ""),
        schema="farms",
    )
    op.drop_constraint(
        "uq_cost_allocations_tenant_req_item_evento",
        "cost_allocations",
        type_="unique",
        schema="farms",
    )
    op.drop_constraint(
        "fk_cost_allocations_tenant_req_item_evento",
        "cost_allocations",
        type_="foreignkey",
        schema="farms",
    )
    op.drop_column("cost_allocations", "requisicao_item_evento_id", schema="farms")
