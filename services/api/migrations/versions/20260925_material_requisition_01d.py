"""MATERIAL-REQUISITION-FLOW-01D: reservation lifecycle and physical handoff.

Adds only state needed by canonical reservation/partial delivery and makes the
event-to-physical-movement association one-to-one. No historical backfill is
performed and no legacy movement is reclassified.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260925_material_requisition_01d"
down_revision: str | Sequence[str] | None = "20260925_material_requisition_01c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "estoque_reservas",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
        schema="farms",
    )
    op.add_column(
        "estoque_reservas",
        sa.Column("quantidade_consumida", sa.Numeric(18, 6), nullable=False, server_default="0"),
        schema="farms",
    )
    op.add_column(
        "estoque_reservas",
        sa.Column("client_operation_id", sa.String(length=120), nullable=True),
        schema="farms",
    )
    op.create_unique_constraint(
        "uq_estoque_reservas_tenant_client_operation",
        "estoque_reservas",
        ["tenant_id", "client_operation_id"],
        schema="farms",
    )
    op.create_check_constraint(
        "ck_estoque_reservas_quantidade_positiva",
        "estoque_reservas",
        "quantidade > 0",
        schema="farms",
    )
    op.create_check_constraint(
        "ck_estoque_reservas_quantidade_consumida",
        "estoque_reservas",
        "quantidade_consumida >= 0 AND quantidade_consumida <= quantidade",
        schema="farms",
    )
    op.create_check_constraint(
        "ck_estoque_reservas_status",
        "estoque_reservas",
        "status IN ('ATIVA','PARCIALMENTE_CONSUMIDA','CONSUMIDA','LIBERADA','CANCELADA')",
        schema="farms",
    )
    op.create_unique_constraint(
        "uq_estoque_movimentos_tenant_req_item_evento",
        "estoque_movimentos",
        ["tenant_id", "requisicao_item_evento_id"],
        schema="farms",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_estoque_movimentos_tenant_req_item_evento",
        "estoque_movimentos",
        type_="unique",
        schema="farms",
    )
    op.drop_constraint("ck_estoque_reservas_status", "estoque_reservas", type_="check", schema="farms")
    op.drop_constraint(
        "ck_estoque_reservas_quantidade_consumida",
        "estoque_reservas",
        type_="check",
        schema="farms",
    )
    op.drop_constraint(
        "ck_estoque_reservas_quantidade_positiva",
        "estoque_reservas",
        type_="check",
        schema="farms",
    )
    op.drop_constraint(
        "uq_estoque_reservas_tenant_client_operation",
        "estoque_reservas",
        type_="unique",
        schema="farms",
    )
    op.drop_column("estoque_reservas", "client_operation_id", schema="farms")
    op.drop_column("estoque_reservas", "quantidade_consumida", schema="farms")
    op.alter_column(
        "estoque_reservas",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
        schema="farms",
    )
