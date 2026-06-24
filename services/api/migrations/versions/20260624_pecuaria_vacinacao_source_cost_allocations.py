"""allow pecuaria vacinacao source in cost_allocations

Revision ID: 20260624_pecuaria_vacinacao_source_cost_allocations
Revises: 20260624_pecuaria_vacinacao_origem_estoque
Create Date: 2026-06-24 14:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260624_pecuaria_vacinacao_source_cost_allocations"
down_revision = "20260624_pecuaria_vacinacao_origem_estoque"
branch_labels = None
depends_on = None


def _rebuild_check_constraint() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("cost_allocations")}
    if "ck_cost_allocations_source" in constraints:
        op.drop_constraint("ck_cost_allocations_source", "cost_allocations", type_="check")
    op.create_check_constraint(
        "ck_cost_allocations_source",
        "cost_allocations",
        "source IN ('OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL','PECUARIA_VACINACAO')",
    )


def upgrade() -> None:
    _rebuild_check_constraint()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("cost_allocations")}
    if "ck_cost_allocations_source" in constraints:
        op.drop_constraint("ck_cost_allocations_source", "cost_allocations", type_="check")
    op.create_check_constraint(
        "ck_cost_allocations_source",
        "cost_allocations",
        "source IN ('OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL')",
    )
