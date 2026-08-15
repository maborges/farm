"""Adiciona custo_unitario_producao em agricola_produtos_colhidos — OPERATIONS-GAP-01 Alternativa B

Snapshot de custo unitário calculado no momento da criação do lote
(custo_acumulado_do_PU / quantidade_acumulada_do_PU até a data), gravado
para performance e estabilidade histórica. Campo nullable: lotes antigos
(sem backfill) e lotes cujo PU seja ambíguo/inexistente ficam sem valor.

Revision ID: 20260815_produto_colhido_custo
Revises: tenant_fk_repair_01d2
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_produto_colhido_custo"
down_revision = "tenant_fk_repair_01d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agricola_produtos_colhidos",
        sa.Column("custo_unitario_producao", sa.Numeric(14, 4), nullable=True),
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_column("agricola_produtos_colhidos", "custo_unitario_producao")
    op.execute("COMMIT")
