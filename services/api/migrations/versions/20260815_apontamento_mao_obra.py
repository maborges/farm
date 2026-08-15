"""cria operacional_apontamentos_mao_obra

OPERATIONS-GAP-01 §21.14: elo estruturado que faltava entre execução real de
mão de obra manual (sem equipamento) e OperacaoAgricola/CostAllocation —
equivalente de frota_apontamentos_uso, mas sem equipamento_id obrigatório.

Revision ID: 20260815_apontamento_mao_obra
Revises: 20260815_estoque_origem_perda
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_apontamento_mao_obra"
down_revision = "20260815_estoque_origem_perda"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operacional_apontamentos_mao_obra",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("pessoa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("data", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("turno", sa.String(10), nullable=False, server_default="INTEGRAL"),
        sa.Column("horas_trabalhadas", sa.Numeric(6, 2), nullable=False),
        sa.Column("unidade_produtiva_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("unidades_produtivas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("safra_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("production_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("production_units.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("talhao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operacao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("tipo_operacao", sa.String(50), nullable=True),
        sa.Column("quantidade_pessoas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("custo_hora_snapshot", sa.Numeric(15, 4), nullable=True),
        sa.Column("custo_total", sa.Numeric(15, 2), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_table("operacional_apontamentos_mao_obra")
    op.execute("COMMIT")
