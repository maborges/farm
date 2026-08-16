"""cria tabela imoveis_sistemas_irrigacao

Módulo de irrigação reposicionado de dentro do stub morto em
agricola/ndvi_avancado/ para imoveis/ (infraestrutura fixa do imóvel,
mesmo domínio de Benfeitoria). OPERATIONS-GAP-01 §21.34.

Revision ID: 20260816_imoveis_irrigacao
Revises: 20260816_depreciacao_linear
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260816_imoveis_irrigacao"
down_revision = "20260816_depreciacao_linear"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "imoveis_sistemas_irrigacao",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("imovel_id", UUID(as_uuid=True), sa.ForeignKey("imoveis_rurais.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unidade_produtiva_id", UUID(as_uuid=True), sa.ForeignKey("unidades_produtivas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("fonte_agua", sa.String(30), nullable=True),
        sa.Column("area_irrigada_ha", sa.Numeric(10, 2), nullable=True),
        sa.Column("vazao_m3h", sa.Numeric(10, 2), nullable=True),
        sa.Column("pressao_bar", sa.Numeric(6, 2), nullable=True),
        sa.Column("potencia_motor_cv", sa.Numeric(8, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ATIVO"),
        sa.Column("data_instalacao", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_imoveis_sistemas_irrigacao_tenant_id", "imoveis_sistemas_irrigacao", ["tenant_id"])
    op.create_index("ix_imoveis_sistemas_irrigacao_imovel_id", "imoveis_sistemas_irrigacao", ["imovel_id"])
    op.create_index("ix_imoveis_sistemas_irrigacao_unidade_produtiva_id", "imoveis_sistemas_irrigacao", ["unidade_produtiva_id"])
    op.execute("COMMIT")


def downgrade():
    op.drop_table("imoveis_sistemas_irrigacao")
    op.execute("COMMIT")
