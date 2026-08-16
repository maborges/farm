"""manutencao benfeitoria (OPERATIONS-GAP-01 §21.33)

Revision ID: 20260815_manutencao_benfeitoria
Revises: 20260815_compras_item_up_servico
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_manutencao_benfeitoria"
down_revision = "20260815_compras_item_up_servico"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "imoveis_planos_manutencao_benfeitoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("benfeitoria_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("imoveis_benfeitorias.id", ondelete="CASCADE"), nullable=False),
        sa.Column("descricao", sa.String(length=150), nullable=False),
        sa.Column("frequencia_dias", sa.Integer(), nullable=True),
        sa.Column("ultimo_registro_data", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_imoveis_planos_manutencao_benfeitoria_tenant_id", "imoveis_planos_manutencao_benfeitoria", ["tenant_id"])
    op.create_index("ix_imoveis_planos_manutencao_benfeitoria_benfeitoria_id", "imoveis_planos_manutencao_benfeitoria", ["benfeitoria_id"])
    op.create_index(
        "ix_imoveis_planos_manut_tenant_benfeitoria", "imoveis_planos_manutencao_benfeitoria",
        ["tenant_id", "benfeitoria_id"],
    )

    op.create_table(
        "imoveis_ordens_servico_benfeitoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("benfeitoria_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("imoveis_benfeitorias.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plano_manutencao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("imoveis_planos_manutencao_benfeitoria.id", ondelete="SET NULL"), nullable=True),
        sa.Column("safra_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="SET NULL"), nullable=True),
        sa.Column("talhao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True),
        sa.Column("numero_os", sa.String(length=20), nullable=False, unique=True),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ABERTA"),
        sa.Column("descricao_problema", sa.String(length=500), nullable=False),
        sa.Column("data_abertura", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("data_conclusao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aberta_por_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("encerrada_por_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("custo_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_imoveis_ordens_servico_benfeitoria_tenant_id", "imoveis_ordens_servico_benfeitoria", ["tenant_id"])
    op.create_index("ix_imoveis_ordens_servico_benfeitoria_benfeitoria_id", "imoveis_ordens_servico_benfeitoria", ["benfeitoria_id"])
    op.create_index("ix_imoveis_ordens_servico_benfeitoria_numero_os", "imoveis_ordens_servico_benfeitoria", ["numero_os"], unique=True)
    op.create_index("ix_imoveis_ordens_servico_benfeitoria_safra_id", "imoveis_ordens_servico_benfeitoria", ["safra_id"])
    op.create_index("ix_imoveis_ordens_servico_benfeitoria_talhao_id", "imoveis_ordens_servico_benfeitoria", ["talhao_id"])
    op.create_index("ix_imoveis_ordens_servico_benfeitoria_aberta_por_id", "imoveis_ordens_servico_benfeitoria", ["aberta_por_id"])
    op.create_index("ix_imoveis_ordens_servico_benfeitoria_encerrada_por_id", "imoveis_ordens_servico_benfeitoria", ["encerrada_por_id"])
    op.create_index(
        "ix_imoveis_os_benfeitoria_tenant_benfeitoria", "imoveis_ordens_servico_benfeitoria",
        ["tenant_id", "benfeitoria_id"],
    )
    op.create_index(
        "ix_imoveis_os_benfeitoria_tenant_status", "imoveis_ordens_servico_benfeitoria",
        ["tenant_id", "status"],
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_table("imoveis_ordens_servico_benfeitoria")
    op.drop_table("imoveis_planos_manutencao_benfeitoria")
    op.execute("COMMIT")
