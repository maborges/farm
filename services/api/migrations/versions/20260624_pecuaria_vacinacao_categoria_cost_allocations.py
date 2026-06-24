"""allow sanitario category in cost_allocations

Revision ID: 20260624_pecuaria_vacinacao_categoria_cost_allocations
Revises: 20260624_pecuaria_vacinacao_source_cost_allocations
Create Date: 2026-06-24 14:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260624_pecuaria_vacinacao_categoria_cost_allocations"
down_revision = "20260624_pecuaria_vacinacao_source_cost_allocations"
branch_labels = None
depends_on = None


def _rebuild_check_constraint() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("cost_allocations")}
    if "ck_cost_allocations_category" in constraints:
        op.drop_constraint("ck_cost_allocations_category", "cost_allocations", type_="check")
    op.create_check_constraint(
        "ck_cost_allocations_category",
        "cost_allocations",
        "cost_category IN ('INSUMO','MAO_OBRA','MAQUINARIO','SERVICO','DESPESA_FINANCEIRA','OUTROS','SANITARIO')",
    )


def upgrade() -> None:
    _rebuild_check_constraint()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("cost_allocations")}
    if "ck_cost_allocations_category" in constraints:
        op.drop_constraint("ck_cost_allocations_category", "cost_allocations", type_="check")
    op.create_check_constraint(
        "ck_cost_allocations_category",
        "cost_allocations",
        "cost_category IN ('INSUMO','MAO_OBRA','MAQUINARIO','SERVICO','DESPESA_FINANCEIRA','OUTROS')",
    )
