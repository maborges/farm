"""Adiciona modo híbrido e campos econômicos aos lotes pecuários.

Revision ID: 20261120_pecuaria_lote_hibrido
Revises: 20261119_rls_global_catalog_admin_write
Create Date: 2026-11-20 19:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision: str = "20261120_pecuaria_lote_hibrido"
down_revision: str | None = "20261119_rls_global_catalog_admin_write"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adiciona suporte a gestão híbrida e parâmetros econômicos em pec_lotes."""
    op.add_column(
        "pec_lotes",
        sa.Column("modo_gestao", sa.String(length=20), nullable=False, server_default="POR_LOTE"),
    )
    op.add_column(
        "pec_lotes",
        sa.Column("rendimento_carcaca_pct", sa.Float(), nullable=False, server_default="50.0"),
    )
    op.add_column(
        "pec_lotes",
        sa.Column("peso_inicial_medio_kg", sa.Float(), nullable=True),
    )
    op.add_column(
        "pec_lotes",
        sa.Column("valor_aquisicao_total", sa.Float(), nullable=True),
    )
    op.add_column(
        "pec_lotes",
        sa.Column("cotacao_arroba_override", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Remove os campos híbridos e econômicos de pec_lotes."""
    op.drop_column("pec_lotes", "cotacao_arroba_override")
    op.drop_column("pec_lotes", "valor_aquisicao_total")
    op.drop_column("pec_lotes", "peso_inicial_medio_kg")
    op.drop_column("pec_lotes", "rendimento_carcaca_pct")
    op.drop_column("pec_lotes", "modo_gestao")
