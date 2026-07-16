"""step28: add calculated georeferenced area to unidades_produtivas

Revision ID: step28_area_total_calculada_unidades_produtivas
Revises: step27_rename_insumo_id
Create Date: 2026-07-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "step28_area_total_calculada_unidades_produtivas"
down_revision = "step27_rename_insumo_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "unidades_produtivas",
        sa.Column(
            "area_total_calculada_ha",
            sa.Numeric(12, 4),
            nullable=True,
            comment="Área calculada por georreferenciamento; leitura somente.",
        ),
    )


def downgrade() -> None:
    op.drop_column("unidades_produtivas", "area_total_calculada_ha")
