"""Hedge MVP — ContratosFuturosV2 e HedgeRegistrosV2

Revision ID: hedge_mvp_001
Revises: c55e2c636a9b_performance_indexes
Create Date: 2026-06-14

DECISÃO DE ARQUITETURA:
- Tabelas nomeadas com sufixo _v2 para evitar conflito com
  a migration legada fase3_sprints27_33_final.py que criou
  e reverteu (downgrade) as tabelas originais sem sufixo.
- Colunas tenant_id e IDs como UUID (em vez de String/Integer legado).
- safra_id adicionado em ambas as tabelas (ausente na versão legada).
- commodity_id (UUID FK para cadastros_commodities) adicionado em contratos_futuros_v2.
- Módulo: F4_HEDGING (não EXT_IA).
- HedgePosition NÃO é tabela — projeção calculada via query.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "hedge_mvp_001"
down_revision = "c55e2c636a9b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # contratos_futuros_v2
    # ------------------------------------------------------------------
    op.create_table(
        "contratos_futuros_v2",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "safra_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("safras.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "commodity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cadastros_commodities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("commodity", sa.String(50), nullable=False),
        sa.Column("mercado", sa.String(50), nullable=True),
        sa.Column("codigo_contrato", sa.String(50), nullable=True),
        sa.Column("mes_vencimento", sa.String(7), nullable=True),
        sa.Column("tipo_posicao", sa.String(10), nullable=False, server_default="VENDA"),
        sa.Column("quantidade", sa.Numeric(14, 4), nullable=False),
        sa.Column("unidade", sa.String(20), nullable=True, server_default="sc"),
        sa.Column("preco_contratado", sa.Numeric(14, 4), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ABERTO"),
        sa.Column("data_liquidacao", sa.Date, nullable=True),
        sa.Column("preco_liquidacao", sa.Numeric(14, 4), nullable=True),
        sa.Column("resultado", sa.Numeric(14, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_contratos_futuros_v2_tenant_id",
        "contratos_futuros_v2",
        ["tenant_id"],
    )
    op.create_index(
        "ix_contratos_futuros_v2_tenant_status",
        "contratos_futuros_v2",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_contratos_futuros_v2_tenant_safra",
        "contratos_futuros_v2",
        ["tenant_id", "safra_id"],
    )

    # ------------------------------------------------------------------
    # hedge_registros_v2
    # ------------------------------------------------------------------
    op.create_table(
        "hedge_registros_v2",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contrato_futuro_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contratos_futuros_v2.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "safra_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("safras.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tipo", sa.String(30), nullable=False, server_default="ABERTURA"),
        sa.Column("quantidade", sa.Numeric(14, 4), nullable=False),
        sa.Column("preco", sa.Numeric(14, 4), nullable=False),
        sa.Column("data_operacao", sa.Date, nullable=False),
        sa.Column("base", sa.Numeric(14, 4), nullable=True),
        sa.Column("resultado_papel", sa.Numeric(14, 4), nullable=True),
        sa.Column("resultado_fisico", sa.Numeric(14, 4), nullable=True),
        sa.Column("resultado_liquido", sa.Numeric(14, 4), nullable=True),
        sa.Column("observacoes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_hedge_registros_v2_tenant_id",
        "hedge_registros_v2",
        ["tenant_id"],
    )
    op.create_index(
        "ix_hedge_registros_v2_tenant_contrato",
        "hedge_registros_v2",
        ["tenant_id", "contrato_futuro_id"],
    )
    op.create_index(
        "ix_hedge_registros_v2_tenant_safra",
        "hedge_registros_v2",
        ["tenant_id", "safra_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_hedge_registros_v2_tenant_safra", table_name="hedge_registros_v2")
    op.drop_index("ix_hedge_registros_v2_tenant_contrato", table_name="hedge_registros_v2")
    op.drop_index("ix_hedge_registros_v2_tenant_id", table_name="hedge_registros_v2")
    op.drop_table("hedge_registros_v2")

    op.drop_index("ix_contratos_futuros_v2_tenant_safra", table_name="contratos_futuros_v2")
    op.drop_index("ix_contratos_futuros_v2_tenant_status", table_name="contratos_futuros_v2")
    op.drop_index("ix_contratos_futuros_v2_tenant_id", table_name="contratos_futuros_v2")
    op.drop_table("contratos_futuros_v2")
