"""remove legacy rural-area land registry path

Revision ID: 20260717_remove_area_matriculas_legacy
Revises: 20260716_config_up_security_freeze
Create Date: 2026-07-17 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260717_remove_area_matriculas_legacy"
down_revision = "20260716_config_up_security_freeze"
branch_labels = None
depends_on = None


TABLE_NAME = "cadastros_areas_matriculas"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM cadastros_areas_matriculas) THEN
                    RAISE EXCEPTION 'legacy area matriculas contains data; migrate before removal';
                END IF;
            END
            $$
            """
        )
    )
    op.drop_table(TABLE_NAME)


def downgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("area_id", sa.Uuid(), nullable=False),
        sa.Column("numero_matricula", sa.String(length=100), nullable=False),
        sa.Column("cartorio", sa.String(length=200), nullable=True),
        sa.Column("comarca", sa.String(length=100), nullable=True),
        sa.Column("area_matricula_ha", sa.Float(), nullable=True),
        sa.Column("car_numero", sa.String(length=100), nullable=True),
        sa.Column("nirf", sa.String(length=30), nullable=True),
        sa.Column("incra", sa.String(length=30), nullable=True),
        sa.Column("ccir", sa.String(length=30), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("livro", sa.String(length=50), nullable=True),
        sa.Column("folha", sa.String(length=50), nullable=True),
        sa.Column("data_registro", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sncr", sa.String(length=30), nullable=True),
        sa.Column("itr_numero", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["area_id"],
            ["cadastros_areas_rurais.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cadastros_areas_matriculas_area_id",
        TABLE_NAME,
        ["area_id"],
        unique=False,
    )
