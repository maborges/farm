"""create agro collector foundation tables

Revision ID: 20261122_agro_collector_foundation
Revises: 20261120_pecuaria_lote_hibrido
Create Date: 2026-11-22 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261122_agro_collector_foundation"
down_revision = "20261120_pecuaria_lote_hibrido"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria as 5 tabelas globais do coletor multi-fonte de dados agropecuários."""
    op.create_table(
        "agro_data_sources",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False, server_default="MERCADO"),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("sigla", sa.String(length=40), nullable=False),
        sa.Column("tipo_licenca", sa.String(length=30), nullable=False),
        sa.Column("termo_autorizacao_ref", sa.Text(), nullable=True),
        sa.Column("atribuicao_obrigatoria", sa.String(length=255), nullable=True),
        sa.Column("uf_padrao", sa.String(length=2), nullable=False, server_default="BR"),
        sa.Column("praca_padrao", sa.String(length=120), nullable=True),
        sa.Column("dominios_whitelist", sa.JSON(), nullable=False),
        sa.Column("url_principal", sa.Text(), nullable=False),
        sa.Column("url_indice", sa.Text(), nullable=True),
        sa.Column("estrategia_coleta", sa.String(length=40), nullable=False),
        sa.Column("config_extrator", sa.JSON(), nullable=False),
        sa.Column("cron_ou_intervalo_seg", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column(
            "auto_publish_policy",
            sa.String(length=40),
            nullable=False,
            server_default="AUTO_SE_GUARDRAILS_OK",
        ),
        sa.Column("max_variacao_pct", sa.Numeric(5, 2), nullable=False, server_default="12.00"),
        sa.Column("max_defasagem_dias", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("prioridade_exibicao", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("falhas_consecutivas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ultima_execucao_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_sucesso_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proximo_ciclo_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_agro_data_sources_slug", "agro_data_sources", ["slug"], unique=True)

    op.create_table(
        "agro_ingestion_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("trigger_tipo", sa.String(length=30), nullable=False, server_default="AGENDADO"),
        sa.Column("executado_por", sa.String(length=120), nullable=True),
        sa.Column("url_efetiva", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_modified", sa.String(length=120), nullable=True),
        sa.Column("sha256_bruto", sa.String(length=64), nullable=True),
        sa.Column("tamanho_bytes", sa.BigInteger(), nullable=True),
        sa.Column("skipped_unchanged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("modelo_ia", sa.String(length=80), nullable=True),
        sa.Column("tokens_entrada", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_saida", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("custo_estimado_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("total_extraidos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_publicados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_quarentena", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_rejeitados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erro_resumo", sa.Text(), nullable=True),
        sa.Column("sugestao_sentinela", sa.JSON(), nullable=True),
        sa.Column(
            "iniciado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["agro_data_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agro_ingestion_runs_source_iniciado",
        "agro_ingestion_runs",
        ["source_id", "iniciado_em"],
    )
    op.create_index(
        "ix_agro_ingestion_runs_source_sha256",
        "agro_ingestion_runs",
        ["source_id", "sha256_bruto"],
    )

    op.create_table(
        "agro_ingestion_artifacts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("compressao", sa.String(length=16), nullable=False, server_default="gzip"),
        sa.Column("conteudo_comprimido", sa.LargeBinary(), nullable=True),
        sa.Column("tamanho_original_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tamanho_comprimido_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("retencao_ate", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expurgado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agro_ingestion_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["agro_data_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agro_ingestion_artifacts_run_id", "agro_ingestion_artifacts", ["run_id"])
    op.create_index(
        "ix_agro_ingestion_artifacts_source_id", "agro_ingestion_artifacts", ["source_id"]
    )
    op.create_index("ix_agro_ingestion_artifacts_sha256", "agro_ingestion_artifacts", ["sha256"])
    op.create_index(
        "ix_agro_ingestion_artifacts_retencao",
        "agro_ingestion_artifacts",
        ["retencao_ate", "expurgado_em"],
    )

    op.create_table(
        "agro_staging_observations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("commodity_id", sa.String(length=64), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("praca", sa.String(length=120), nullable=False),
        sa.Column("tipo_preco", sa.String(length=50), nullable=False),
        sa.Column("periodicidade", sa.String(length=20), nullable=False),
        sa.Column("data_referencia", sa.Date(), nullable=False),
        sa.Column("valor_normalizado", sa.Numeric(14, 4), nullable=False),
        sa.Column("moeda", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("unidade_normalizada", sa.String(length=60), nullable=False),
        sa.Column("valor_original", sa.Numeric(14, 4), nullable=False),
        sa.Column("unidade_original", sa.String(length=60), nullable=False),
        sa.Column("fator_conversao", sa.Numeric(14, 6), nullable=False, server_default="1.000000"),
        sa.Column("transformacao_aplicada", sa.String(length=255), nullable=True),
        sa.Column("trecho_evidencia", sa.Text(), nullable=False),
        sa.Column("registro_origem", sa.String(length=120), nullable=True),
        sa.Column("confianca_extracao", sa.Numeric(4, 3), nullable=False, server_default="1.000"),
        sa.Column("flags_anomalia", sa.JSON(), nullable=False),
        sa.Column(
            "status_revisao",
            sa.String(length=30),
            nullable=False,
            server_default="PENDENTE_REVISAO",
        ),
        sa.Column("revisado_por", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("revisado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("justificativa_revisao", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["revisado_por"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["agro_ingestion_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["agro_data_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agro_staging_observations_run_id", "agro_staging_observations", ["run_id"])
    op.create_index(
        "ix_agro_staging_observations_source_id", "agro_staging_observations", ["source_id"]
    )
    op.create_index(
        "ix_agro_staging_pendentes",
        "agro_staging_observations",
        ["status_revisao", "created_at"],
        postgresql_where=sa.text("status_revisao = 'PENDENTE_REVISAO'"),
        sqlite_where=sa.text("status_revisao = 'PENDENTE_REVISAO'"),
    )

    op.create_table(
        "agro_market_observations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("staging_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("commodity_id", sa.String(length=64), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("praca", sa.String(length=120), nullable=False),
        sa.Column("tipo_preco", sa.String(length=50), nullable=False),
        sa.Column("periodicidade", sa.String(length=20), nullable=False),
        sa.Column("data_referencia", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(14, 4), nullable=False),
        sa.Column("moeda", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("unidade", sa.String(length=60), nullable=False),
        sa.Column("valor_original", sa.Numeric(14, 4), nullable=False),
        sa.Column("unidade_original", sa.String(length=60), nullable=False),
        sa.Column("transformacao_aplicada", sa.String(length=255), nullable=True),
        sa.Column("variacao_anterior_abs", sa.Numeric(14, 4), nullable=True),
        sa.Column("variacao_anterior_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("documento_oficial", sa.Text(), nullable=True),
        sa.Column("documento_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("registro_origem", sa.String(length=120), nullable=True),
        sa.Column(
            "publicado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["run_id"], ["agro_ingestion_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["agro_data_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["staging_id"], ["agro_staging_observations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "commodity_id",
            "uf",
            "praca",
            "data_referencia",
            name="uq_agro_mkt_obs_serie",
        ),
    )
    op.create_index(
        "ix_agro_mkt_obs_uf_comm_data",
        "agro_market_observations",
        ["uf", "commodity_id", "data_referencia"],
        postgresql_where=sa.text("ativo = true"),
        sqlite_where=sa.text("ativo = 1"),
    )
    op.create_index(
        "ix_agro_mkt_obs_comm_data",
        "agro_market_observations",
        ["commodity_id", "data_referencia"],
        postgresql_where=sa.text("ativo = true"),
        sqlite_where=sa.text("ativo = 1"),
    )


def downgrade() -> None:
    """Remove as tabelas do coletor multi-fonte em ordem reversa às dependências."""
    op.drop_index("ix_agro_mkt_obs_comm_data", table_name="agro_market_observations")
    op.drop_index("ix_agro_mkt_obs_uf_comm_data", table_name="agro_market_observations")
    op.drop_table("agro_market_observations")

    op.drop_index("ix_agro_staging_pendentes", table_name="agro_staging_observations")
    op.drop_index("ix_agro_staging_observations_source_id", table_name="agro_staging_observations")
    op.drop_index("ix_agro_staging_observations_run_id", table_name="agro_staging_observations")
    op.drop_table("agro_staging_observations")

    op.drop_index("ix_agro_ingestion_artifacts_retencao", table_name="agro_ingestion_artifacts")
    op.drop_index("ix_agro_ingestion_artifacts_sha256", table_name="agro_ingestion_artifacts")
    op.drop_index("ix_agro_ingestion_artifacts_source_id", table_name="agro_ingestion_artifacts")
    op.drop_index("ix_agro_ingestion_artifacts_run_id", table_name="agro_ingestion_artifacts")
    op.drop_table("agro_ingestion_artifacts")

    op.drop_index("ix_agro_ingestion_runs_source_sha256", table_name="agro_ingestion_runs")
    op.drop_index("ix_agro_ingestion_runs_source_iniciado", table_name="agro_ingestion_runs")
    op.drop_table("agro_ingestion_runs")

    op.drop_index("ix_agro_data_sources_slug", table_name="agro_data_sources")
    op.drop_table("agro_data_sources")
