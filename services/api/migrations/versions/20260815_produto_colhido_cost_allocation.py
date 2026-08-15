"""Cria agricola_produto_colhido_cost_allocations — OPERATIONS-GAP-01 Alternativa C

Tabela de junção persistindo o rateio entre ProdutoColhido (lote) e
CostAllocation (custo do PU), populada por reconciliação sob demanda
(agricola/custos/lote_allocation_service.py) e permitindo override manual
auditável (origem_calculo=MANUAL + justificativa).

Revision ID: 20260815_produto_colhido_cost_alloc
Revises: 20260815_produto_colhido_custo
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_produto_colhido_cost_alloc"
down_revision = "20260815_produto_colhido_custo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agricola_produto_colhido_cost_allocations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("produto_colhido_id", sa.Uuid(as_uuid=True), sa.ForeignKey("agricola_produtos_colhidos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("cost_allocation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("cost_allocations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("valor_atribuido", sa.Numeric(15, 2), nullable=False),
        sa.Column("percentual_atribuido", sa.Numeric(7, 4), nullable=False),
        sa.Column("origem_calculo", sa.String(20), nullable=False, server_default="AUTOMATICO"),
        sa.Column("justificativa", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("produto_colhido_id", "cost_allocation_id", name="uq_produto_colhido_cost_allocation"),
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_table("agricola_produto_colhido_cost_allocations")
    op.execute("COMMIT")
