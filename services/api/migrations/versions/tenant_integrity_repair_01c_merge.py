"""Merge: 20260717_remove_area_matriculas_legacy + tenant_integrity_repair_01c

Unifica os dois heads paralelos gerados quando a migration 01C foi criada a
partir de 265b28773962 em vez de 20260717_remove_area_matriculas_legacy.
Não contém alterações de schema — apenas reconcilia a cadeia Alembic.

Revision ID: tenant_integrity_repair_01c_merge
Revises: 20260717_remove_area_matriculas_legacy, tenant_integrity_repair_01c
Create Date: 2026-07-17
"""
from alembic import op

revision = "tenant_integrity_repair_01c_merge"
down_revision = (
    "20260717_remove_area_matriculas_legacy",
    "tenant_integrity_repair_01c",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
