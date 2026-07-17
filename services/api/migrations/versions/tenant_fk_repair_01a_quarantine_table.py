"""tenant_fk_repair_01a: criar tabela tenant_fk_quarantine

Revision ID: tenant_fk_repair_01a
Revises: 5c6895a7  (ajustar para o head atual)
Create Date: 2026-07-17

Propósito: suporte ao plano TENANT-FK-REPAIR-01A — quarentena de registros
com tenant_id cruzado entre tenants. Não altera nenhuma tabela de negócio.
"""
from alembic import op
import sqlalchemy as sa

revision = "tenant_fk_repair_01a"
down_revision = None  # ajustar para o revision head atual
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_fk_quarantine",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_table", sa.Text(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("source_tenant_id", sa.UUID(), nullable=False),
        sa.Column("parent_table", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=False),
        sa.Column("parent_tenant_id", sa.UUID(), nullable=False),
        sa.Column("row_snapshot", sa.JSON(), nullable=False),
        sa.Column("quarantined_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolution_action", sa.Text(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="farms",
    )
    op.create_index(
        "idx_tfq_source_table", "tenant_fk_quarantine",
        ["source_table"], schema="farms"
    )
    op.create_index(
        "idx_tfq_source_tenant", "tenant_fk_quarantine",
        ["source_tenant_id"], schema="farms"
    )
    op.create_index(
        "idx_tfq_resolved", "tenant_fk_quarantine",
        ["resolved"], schema="farms",
        postgresql_where=sa.text("NOT resolved")
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_table("tenant_fk_quarantine", schema="farms")
    op.execute("COMMIT")
