"""recria prescricoes_vra alinhada ao schema/model realmente usados por agricola/prescricoes

A tabela prescricoes_vra existente (colunas tipo/elemento/dose_media/unidade_produtiva_id,
PK integer) nunca foi consumida por nenhum código ativo: o único módulo que a usa de fato
(agricola/prescricoes/router.py + schemas.py) sempre esperou um schema diferente
(nome/talhao_id/safra_id/tipo_operacao/insumo/camadas_json, PK uuid), o mesmo já implementado
no frontend (apps/web .../dashboard/agricola/prescricoes/page.tsx). O mismatch fazia
POST /api/v1/prescricoes quebrar em runtime. Tabela confirmada vazia (0 linhas) em produção
antes desta migration — recriação segura, sem perda de dado.

Revision ID: 20260815_prescricoes_vra_schema
Revises: 20260815_fix_ck_estoque_origem
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_prescricoes_vra_schema"
down_revision = "20260815_fix_ck_estoque_origem"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("prescricoes_vra")
    op.create_table(
        "prescricoes_vra",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("talhao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_areas_rurais.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_operacao", sa.String(50), nullable=True),
        sa.Column("insumo", sa.String(100), nullable=True),
        sa.Column("camadas_json", sa.JSON(), nullable=True),
        sa.Column("area_total_ha", sa.Numeric(12, 2), nullable=True),
        sa.Column("quantidade_total_estimada", sa.Numeric(12, 2), nullable=True),
        sa.Column("data_prescricao", sa.Date(), nullable=True),
        sa.Column("arquivo_original_url", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_table("prescricoes_vra")
    op.create_table(
        "prescricoes_vra",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("unidade_produtiva_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("unidades_produtivas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("production_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("production_units.id", ondelete="SET NULL"), nullable=True),
        sa.Column("talhao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True),
        sa.Column("safra_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("elemento", sa.String(50), nullable=True),
        sa.Column("dose_media", sa.Float(), nullable=True),
        sa.Column("dose_minima", sa.Float(), nullable=True),
        sa.Column("dose_maxima", sa.Float(), nullable=True),
        sa.Column("unidade", sa.String(20), nullable=True),
        sa.Column("caminho_isoxml", sa.String(500), nullable=True),
        sa.Column("caminho_shapefile", sa.String(500), nullable=True),
        sa.Column("caminho_geojson", sa.String(500), nullable=True),
        sa.Column("grid_tamanho_m", sa.Float(), nullable=True),
        sa.Column("total_pontos", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("aprovada_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("aprovada_em", sa.DateTime(), nullable=True),
        sa.Column("responsavel_tecnico", sa.String(200), nullable=True),
        sa.Column("crt", sa.String(100), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criada_em", sa.DateTime(), nullable=True),
        sa.Column("atualizada_em", sa.DateTime(), nullable=True),
    )
    op.execute("COMMIT")
