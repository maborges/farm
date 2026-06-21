"""bloco canônico de relatorio esg e passaporte de rastreabilidade

Revision ID: 20260621_certificacao_esg_relatorio_passaporte
Revises: 20260621_certificacao_esg_status_nao_conformidade
Create Date: 2026-06-21 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


revision = "20260621_certificacao_esg_relatorio_passaporte"
down_revision = "20260621_certificacao_esg_status_nao_conformidade"
branch_labels = None
depends_on = None


status_relatorio_esg_enum = PGEnum(
    "RASCUNHO",
    "EM_REVISAO",
    "PUBLICADO",
    "CANCELADO",
    name="status_relatorio_esg_enum",
    create_type=False,
)
status_passaporte_enum = PGEnum(
    "RASCUNHO",
    "EM_VALIDACAO",
    "PUBLICADO",
    "REVOGADO",
    name="status_passaporte_enum",
    create_type=False,
)
tipo_evento_passaporte_enum = PGEnum(
    "GERADO",
    "VALIDADO",
    "PUBLICADO",
    "REVOGADO",
    "ATUALIZADO",
    name="tipo_evento_passaporte_enum",
    create_type=False,
)


def _create_enum_types(bind) -> None:
    tipo_evento_passaporte_enum.create(bind, checkfirst=True)


def _drop_enum_types(bind) -> None:
    tipo_evento_passaporte_enum.drop(bind, checkfirst=True)


def _ensure_existing_enum_values() -> None:
    engine = op.get_bind().engine
    with engine.connect() as connection:
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.exec_driver_sql("ALTER TYPE status_relatorio_esg_enum ADD VALUE IF NOT EXISTS 'CANCELADO'")
        connection.exec_driver_sql("ALTER TYPE status_passaporte_enum ADD VALUE IF NOT EXISTS 'EM_VALIDACAO'")
        connection.exec_driver_sql("ALTER TYPE status_passaporte_enum ADD VALUE IF NOT EXISTS 'PUBLICADO'")


def _enable_tenant_rls(table_name: str) -> None:
    policy_prefix = table_name.replace(".", "_")
    op.execute(sa.text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant
            ON "{table_name}"
            FOR SELECT
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant
            ON "{table_name}"
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant
            ON "{table_name}"
            FOR UPDATE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_delete_tenant
            ON "{table_name}"
            FOR DELETE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_existing_enum_values()
    _create_enum_types(bind)

    op.create_table(
        "esg_relatorios",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("programa_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_id", sa.UUID(), nullable=True),
        sa.Column("imovel_rural_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_imovel_id", sa.UUID(), nullable=True),
        sa.Column("responsavel_pessoa_id", sa.UUID(), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("periodo_inicio", sa.Date(), nullable=True),
        sa.Column("periodo_fim", sa.Date(), nullable=True),
        sa.Column("status", status_relatorio_esg_enum, nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=True),
        sa.Column("publico", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["programa_id"], ["certificacao_programas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["propriedade_id"], ["cadastros_propriedades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["imovel_rural_id"], ["imoveis_rurais.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["propriedade_imovel_id"], ["propriedade_imovel.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsavel_pessoa_id"], ["cadastros_pessoas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("btrim(titulo) <> ''", name="ck_esg_relatorios_titulo_nao_vazio"),
        sa.CheckConstraint(
            "periodo_fim IS NULL OR periodo_fim >= periodo_inicio",
            name="ck_esg_relatorios_periodo_valido",
        ),
        sa.CheckConstraint("versao >= 1", name="ck_esg_relatorios_versao_minima"),
        sa.CheckConstraint(
            "status <> 'PUBLICADO' OR snapshot_hash IS NOT NULL",
            name="ck_esg_relatorios_snapshot_publicado",
        ),
        sa.CheckConstraint(
            "status <> 'PUBLICADO' OR publicado_em IS NOT NULL",
            name="ck_esg_relatorios_publicado_em_obrigatorio",
        ),
        sa.CheckConstraint(
            "status <> 'CANCELADO' OR cancelado_em IS NOT NULL",
            name="ck_esg_relatorios_cancelado_em_obrigatorio",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_esg_relatorios_tenant_id", "esg_relatorios", ["tenant_id"], unique=False)
    op.create_index("ix_esg_relatorios_programa_id", "esg_relatorios", ["programa_id"], unique=False)
    op.create_index("ix_esg_relatorios_propriedade_id", "esg_relatorios", ["propriedade_id"], unique=False)
    op.create_index("ix_esg_relatorios_imovel_rural_id", "esg_relatorios", ["imovel_rural_id"], unique=False)
    op.create_index("ix_esg_relatorios_propriedade_imovel_id", "esg_relatorios", ["propriedade_imovel_id"], unique=False)
    op.create_index("ix_esg_relatorios_responsavel_pessoa_id", "esg_relatorios", ["responsavel_pessoa_id"], unique=False)
    op.create_index("ix_esg_relatorios_created_by", "esg_relatorios", ["created_by"], unique=False)
    op.create_index("ix_esg_relatorios_status", "esg_relatorios", ["status"], unique=False)
    op.create_index("ix_esg_relatorios_publico", "esg_relatorios", ["publico"], unique=False)
    op.create_index(
        "ix_esg_relatorios_tenant_status",
        "esg_relatorios",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_esg_relatorios_tenant_publico",
        "esg_relatorios",
        ["tenant_id", "publico"],
        unique=False,
    )
    _enable_tenant_rls("esg_relatorios")

    op.create_table(
        "esg_relatorio_indicadores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("relatorio_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("categoria", sa.String(length=120), nullable=True),
        sa.Column("valor", sa.Numeric(18, 6), nullable=True),
        sa.Column("unidade", sa.String(length=40), nullable=True),
        sa.Column("score", sa.Numeric(10, 2), nullable=True),
        sa.Column("metodologia", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["relatorio_id"], ["esg_relatorios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidencia_id"], ["certificacao_evidencias.id"], ondelete="SET NULL"),
        sa.CheckConstraint("btrim(nome) <> ''", name="ck_esg_relatorio_indicadores_nome_nao_vazio"),
        sa.CheckConstraint("valor IS NULL OR valor >= 0", name="ck_esg_relatorio_indicadores_valor_nao_negativo"),
        sa.CheckConstraint("score IS NULL OR score >= 0", name="ck_esg_relatorio_indicadores_score_nao_negativo"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_esg_relatorio_indicadores_tenant_id",
        "esg_relatorio_indicadores",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_esg_relatorio_indicadores_relatorio_id",
        "esg_relatorio_indicadores",
        ["relatorio_id"],
        unique=False,
    )
    op.create_index(
        "ix_esg_relatorio_indicadores_evidencia_id",
        "esg_relatorio_indicadores",
        ["evidencia_id"],
        unique=False,
    )
    _enable_tenant_rls("esg_relatorio_indicadores")

    op.create_table(
        "esg_relatorio_evidencias",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("relatorio_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["relatorio_id"], ["esg_relatorios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidencia_id"], ["certificacao_evidencias.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_esg_relatorio_evidencias_tenant_id",
        "esg_relatorio_evidencias",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_esg_relatorio_evidencias_relatorio_id",
        "esg_relatorio_evidencias",
        ["relatorio_id"],
        unique=False,
    )
    op.create_index(
        "ix_esg_relatorio_evidencias_evidencia_id",
        "esg_relatorio_evidencias",
        ["evidencia_id"],
        unique=False,
    )
    _enable_tenant_rls("esg_relatorio_evidencias")

    op.create_table(
        "rastreabilidade_passaportes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("programa_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_id", sa.UUID(), nullable=True),
        sa.Column("imovel_rural_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_imovel_id", sa.UUID(), nullable=True),
        sa.Column("lote_rastreabilidade_id", sa.UUID(), nullable=True),
        sa.Column("caderno_lote_comercial_id", sa.UUID(), nullable=True),
        sa.Column("responsavel_pessoa_id", sa.UUID(), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("status", status_passaporte_enum, nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=True),
        sa.Column("publico", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["programa_id"], ["certificacao_programas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["propriedade_id"], ["cadastros_propriedades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["imovel_rural_id"], ["imoveis_rurais.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["propriedade_imovel_id"], ["propriedade_imovel.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lote_rastreabilidade_id"], ["lotes_rastreabilidade.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["caderno_lote_comercial_id"], ["caderno_lotes_comerciais.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsavel_pessoa_id"], ["cadastros_pessoas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("btrim(titulo) <> ''", name="ck_rastreabilidade_passaportes_titulo_nao_vazio"),
        sa.CheckConstraint("versao >= 1", name="ck_rastreabilidade_passaportes_versao_minima"),
        sa.CheckConstraint(
            "status <> 'PUBLICADO' OR snapshot_hash IS NOT NULL",
            name="ck_rastreabilidade_passaportes_snapshot_publicado",
        ),
        sa.CheckConstraint(
            "status <> 'PUBLICADO' OR publicado_em IS NOT NULL",
            name="ck_rastreabilidade_passaportes_publicado_em_obrigatorio",
        ),
        sa.CheckConstraint(
            "status <> 'REVOGADO' OR revogado_em IS NOT NULL",
            name="ck_rastreabilidade_passaportes_revogado_em_obrigatorio",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_tenant_id",
        "rastreabilidade_passaportes",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_programa_id",
        "rastreabilidade_passaportes",
        ["programa_id"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_propriedade_id",
        "rastreabilidade_passaportes",
        ["propriedade_id"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_imovel_rural_id",
        "rastreabilidade_passaportes",
        ["imovel_rural_id"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_propriedade_imovel_id",
        "rastreabilidade_passaportes",
        ["propriedade_imovel_id"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_lote_rastreabilidade_id",
        "rastreabilidade_passaportes",
        ["lote_rastreabilidade_id"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_caderno_lote_comercial_id",
        "rastreabilidade_passaportes",
        ["caderno_lote_comercial_id"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_responsavel_pessoa_id",
        "rastreabilidade_passaportes",
        ["responsavel_pessoa_id"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_created_by",
        "rastreabilidade_passaportes",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_status",
        "rastreabilidade_passaportes",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_publico",
        "rastreabilidade_passaportes",
        ["publico"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_tenant_status",
        "rastreabilidade_passaportes",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_rastreabilidade_passaportes_tenant_publico",
        "rastreabilidade_passaportes",
        ["tenant_id", "publico"],
        unique=False,
    )
    _enable_tenant_rls("rastreabilidade_passaportes")

    op.create_table(
        "rastreabilidade_passaporte_eventos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("passaporte_id", sa.UUID(), nullable=False),
        sa.Column("tipo_evento", tipo_evento_passaporte_enum, nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origem_tipo", sa.String(length=80), nullable=False),
        sa.Column("origem_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["passaporte_id"], ["rastreabilidade_passaportes.id"], ondelete="CASCADE"),
        sa.CheckConstraint("btrim(titulo) <> ''", name="ck_passaporte_eventos_titulo_nao_vazio"),
        sa.CheckConstraint(
            "snapshot_json IS NULL OR snapshot_hash IS NOT NULL",
            name="ck_passaporte_eventos_snapshot_hash_dependente",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_passaporte_eventos_tenant_id",
        "rastreabilidade_passaporte_eventos",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_passaporte_eventos_passaporte_id",
        "rastreabilidade_passaporte_eventos",
        ["passaporte_id"],
        unique=False,
    )
    op.create_index(
        "ix_passaporte_eventos_tipo_evento",
        "rastreabilidade_passaporte_eventos",
        ["tipo_evento"],
        unique=False,
    )
    op.create_index(
        "ix_passaporte_eventos_tenant_tipo_evento",
        "rastreabilidade_passaporte_eventos",
        ["tenant_id", "tipo_evento"],
        unique=False,
    )
    _enable_tenant_rls("rastreabilidade_passaporte_eventos")

    op.create_table(
        "rastreabilidade_passaporte_evidencias",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("passaporte_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["passaporte_id"], ["rastreabilidade_passaportes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidencia_id"], ["certificacao_evidencias.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_passaporte_evidencias_tenant_id",
        "rastreabilidade_passaporte_evidencias",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_passaporte_evidencias_passaporte_id",
        "rastreabilidade_passaporte_evidencias",
        ["passaporte_id"],
        unique=False,
    )
    op.create_index(
        "ix_passaporte_evidencias_evidencia_id",
        "rastreabilidade_passaporte_evidencias",
        ["evidencia_id"],
        unique=False,
    )
    _enable_tenant_rls("rastreabilidade_passaporte_evidencias")


def downgrade() -> None:
    op.drop_table("rastreabilidade_passaporte_evidencias")
    op.drop_table("rastreabilidade_passaporte_eventos")
    op.drop_table("rastreabilidade_passaportes")
    op.drop_table("esg_relatorio_evidencias")
    op.drop_table("esg_relatorio_indicadores")
    op.drop_table("esg_relatorios")

    bind = op.get_bind()
    _drop_enum_types(bind)
