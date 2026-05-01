"""step27: allow null documento for tenants

Revision ID: step27_tenant_documento_nullable
Revises: step26_produto_canonico
Create Date: 2026-05-01
"""

from alembic import op
import sqlalchemy as sa


revision = "step27_tenant_documento_nullable"
down_revision = "step26_produto_canonico"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "tenants",
        "documento",
        existing_type=sa.String(length=20),
        nullable=True,
    )

    op.execute(
        sa.text(
            """
            UPDATE tenants
            SET documento = NULL
            WHERE documento IS NOT NULL
              AND btrim(documento) = ''
            """
        )
    )


def downgrade():
    op.execute(
        sa.text(
            """
            UPDATE tenants
            SET documento = CONCAT('SEM-DOC-', substr(id::text, 1, 8))
            WHERE documento IS NULL
            """
        )
    )

    op.alter_column(
        "tenants",
        "documento",
        existing_type=sa.String(length=20),
        nullable=False,
    )
