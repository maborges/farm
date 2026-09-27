"""MATERIAL-REQUISITION-FLOW-01E: canonical receipt provenance.

The migration only enriches the append-only item-event journal.  Receiving is
an operational acknowledgement and never creates a stock movement.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260925_material_requisition_01e"
down_revision: str | Sequence[str] | None = "20260925_material_requisition_01d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "estoque_requisicao_item_eventos",
        sa.Column(
            "evento_entrega_id",
            sa.UUID(),
            nullable=True,
            comment="Entrega física exata que originou a conferência ou recusa.",
        ),
        schema="farms",
    )
    op.add_column(
        "estoque_requisicao_item_eventos",
        sa.Column(
            "resultado_conferencia",
            sa.String(length=24),
            nullable=True,
            comment="Resultado do aceite: integral, parcial, recusa ou divergência.",
        ),
        schema="farms",
    )
    op.create_index(
        "ix_req_item_evento_evento_entrega",
        "estoque_requisicao_item_eventos",
        ["tenant_id", "evento_entrega_id"],
        schema="farms",
    )
    op.create_check_constraint(
        "ck_req_item_evento_resultado_conferencia",
        "estoque_requisicao_item_eventos",
        "resultado_conferencia IS NULL OR resultado_conferencia IN "
        "('RECEBIDO_INTEGRAL','RECEBIDO_PARCIAL','RECUSADO','DIVERGENTE')",
        schema="farms",
    )
    op.create_foreign_key(
        "fk_req_item_evento_tenant_entrega_origem",
        "estoque_requisicao_item_eventos",
        "estoque_requisicao_item_eventos",
        ["tenant_id", "evento_entrega_id"],
        ["tenant_id", "id"],
        source_schema="farms",
        referent_schema="farms",
        ondelete="NO ACTION",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_req_item_evento_tenant_entrega_origem",
        "estoque_requisicao_item_eventos",
        type_="foreignkey",
        schema="farms",
    )
    op.drop_constraint(
        "ck_req_item_evento_resultado_conferencia",
        "estoque_requisicao_item_eventos",
        type_="check",
        schema="farms",
    )
    op.drop_index(
        "ix_req_item_evento_evento_entrega",
        table_name="estoque_requisicao_item_eventos",
        schema="farms",
    )
    op.drop_column("estoque_requisicao_item_eventos", "resultado_conferencia", schema="farms")
    op.drop_column("estoque_requisicao_item_eventos", "evento_entrega_id", schema="farms")
