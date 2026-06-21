"""lote 2 - evidencias, nao conformidades e planos de acao

Revision ID: 20260621_certificacao_esg_lote2
Revises: 20260621_certificacao_esg_lote1
Create Date: 2026-06-21 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


# revision identifiers, used by Alembic.
revision = "20260621_certificacao_esg_lote2"
down_revision = "20260621_certificacao_esg_lote1"
branch_labels = None
depends_on = None


tipo_evidencia_enum = PGEnum(
    "DOCUMENTO_PDF",
    "FOTO_CAMPO",
    "DADO_SATELITE",
    "OUTRO",
    name="tipo_evidencia_enum",
    create_type=False,
)
severidade_nao_conformidade_enum = PGEnum(
    "MENOR",
    "MAIOR",
    "CRITICA",
    name="severidade_nao_conformidade_enum",
    create_type=False,
)
prioridade_plano_acao_enum = PGEnum(
    "BAIXA",
    "MEDIA",
    "ALTA",
    "URGENTE",
    name="prioridade_plano_acao_enum",
    create_type=False,
)
status_plano_acao_enum = PGEnum(
    "PENDENTE",
    "EM_ANDAMENTO",
    "CONCLUIDO",
    "ATRASADO",
    "CANCELADO",
    name="status_plano_acao_enum",
    create_type=False,
)


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
    op.create_table(
        "certificacao_evidencias",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("programa_id", sa.UUID(), nullable=False),
        sa.Column("checklist_id", sa.UUID(), nullable=True),
        sa.Column("criterio_id", sa.UUID(), nullable=True),
        sa.Column("avaliacao_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_id", sa.UUID(), nullable=True),
        sa.Column("imovel_rural_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_imovel_id", sa.UUID(), nullable=True),
        sa.Column("responsavel_pessoa_id", sa.UUID(), nullable=True),
        sa.Column("tipo_evidencia", tipo_evidencia_enum, nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("origem_tipo", sa.String(length=80), nullable=False),
        sa.Column("origem_id", sa.UUID(), nullable=False),
        sa.Column("arquivo_url", sa.String(length=2048), nullable=True),
        sa.Column("arquivo_hash", sa.String(length=128), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=True),
        sa.Column("publico", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
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
        sa.ForeignKeyConstraint(["checklist_id"], ["certificacao_checklists.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["criterio_id"], ["certificacao_criterios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["certificacao_avaliacoes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["propriedade_id"], ["cadastros_propriedades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["imovel_rural_id"], ["imoveis_rurais.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["propriedade_imovel_id"],
            ["propriedade_imovel.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["responsavel_pessoa_id"],
            ["cadastros_pessoas.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("btrim(titulo) <> ''", name="ck_certificacao_evidencias_titulo_nao_vazio"),
        sa.CheckConstraint(
            "snapshot_json IS NULL OR snapshot_hash IS NOT NULL",
            name="ck_certificacao_evidencias_snapshot_hash_dependente",
        ),
        sa.CheckConstraint(
            "arquivo_url IS NULL OR arquivo_hash IS NOT NULL",
            name="ck_certificacao_evidencias_arquivo_hash_dependente",
        ),
        sa.CheckConstraint(
            "origem_tipo IS NOT NULL AND origem_id IS NOT NULL",
            name="ck_certificacao_evidencias_origem_obrigatoria",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_certificacao_evidencias_tenant_id"), "certificacao_evidencias", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_certificacao_evidencias_programa_id"), "certificacao_evidencias", ["programa_id"], unique=False)
    op.create_index(op.f("ix_certificacao_evidencias_checklist_id"), "certificacao_evidencias", ["checklist_id"], unique=False)
    op.create_index(op.f("ix_certificacao_evidencias_criterio_id"), "certificacao_evidencias", ["criterio_id"], unique=False)
    op.create_index(op.f("ix_certificacao_evidencias_avaliacao_id"), "certificacao_evidencias", ["avaliacao_id"], unique=False)
    op.create_index(op.f("ix_certificacao_evidencias_propriedade_id"), "certificacao_evidencias", ["propriedade_id"], unique=False)
    op.create_index(op.f("ix_certificacao_evidencias_imovel_rural_id"), "certificacao_evidencias", ["imovel_rural_id"], unique=False)
    op.create_index(
        op.f("ix_certificacao_evidencias_propriedade_imovel_id"),
        "certificacao_evidencias",
        ["propriedade_imovel_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_evidencias_tipo_evidencia"),
        "certificacao_evidencias",
        ["tipo_evidencia"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_evidencias_tenant_tipo",
        "certificacao_evidencias",
        ["tenant_id", "tipo_evidencia"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_evidencias_tenant_publico",
        "certificacao_evidencias",
        ["tenant_id", "publico"],
        unique=False,
    )
    _enable_tenant_rls("certificacao_evidencias")

    op.create_table(
        "certificacao_nao_conformidades",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("programa_id", sa.UUID(), nullable=False),
        sa.Column("checklist_id", sa.UUID(), nullable=True),
        sa.Column("criterio_id", sa.UUID(), nullable=True),
        sa.Column("avaliacao_id", sa.UUID(), nullable=True),
        sa.Column("evidencia_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_id", sa.UUID(), nullable=True),
        sa.Column("imovel_rural_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_imovel_id", sa.UUID(), nullable=True),
        sa.Column("responsavel_pessoa_id", sa.UUID(), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("severidade", severidade_nao_conformidade_enum, nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "detectada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("prazo_correcao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolvida_em", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["checklist_id"], ["certificacao_checklists.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["criterio_id"], ["certificacao_criterios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["certificacao_avaliacoes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidencia_id"], ["certificacao_evidencias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["propriedade_id"], ["cadastros_propriedades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["imovel_rural_id"], ["imoveis_rurais.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["propriedade_imovel_id"],
            ["propriedade_imovel.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["responsavel_pessoa_id"],
            ["cadastros_pessoas.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("btrim(titulo) <> ''", name="ck_certificacao_nc_titulo_nao_vazio"),
        sa.CheckConstraint("btrim(status) <> ''", name="ck_certificacao_nc_status_nao_vazio"),
        sa.CheckConstraint(
            "prazo_correcao IS NULL OR prazo_correcao >= detectada_em",
            name="ck_certificacao_nc_prazo_correcao_valido",
        ),
        sa.CheckConstraint(
            "resolvida_em IS NULL OR resolvida_em >= detectada_em",
            name="ck_certificacao_nc_resolucao_valida",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certificacao_nao_conformidades_tenant_id"),
        "certificacao_nao_conformidades",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_nao_conformidades_programa_id"),
        "certificacao_nao_conformidades",
        ["programa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_nao_conformidades_checklist_id"),
        "certificacao_nao_conformidades",
        ["checklist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_nao_conformidades_criterio_id"),
        "certificacao_nao_conformidades",
        ["criterio_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_nao_conformidades_avaliacao_id"),
        "certificacao_nao_conformidades",
        ["avaliacao_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_nao_conformidades_evidencia_id"),
        "certificacao_nao_conformidades",
        ["evidencia_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_nao_conformidades_severidade"),
        "certificacao_nao_conformidades",
        ["severidade"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_nao_conformidades_status"),
        "certificacao_nao_conformidades",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_nc_tenant_status",
        "certificacao_nao_conformidades",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_nc_tenant_severidade",
        "certificacao_nao_conformidades",
        ["tenant_id", "severidade"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_nc_tenant_prazo",
        "certificacao_nao_conformidades",
        ["tenant_id", "prazo_correcao"],
        unique=False,
    )
    _enable_tenant_rls("certificacao_nao_conformidades")

    op.create_table(
        "certificacao_planos_acao",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("programa_id", sa.UUID(), nullable=False),
        sa.Column("nao_conformidade_id", sa.UUID(), nullable=True),
        sa.Column("evidencia_id", sa.UUID(), nullable=True),
        sa.Column("responsavel_pessoa_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_id", sa.UUID(), nullable=True),
        sa.Column("imovel_rural_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_imovel_id", sa.UUID(), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("prioridade", prioridade_plano_acao_enum, nullable=False),
        sa.Column("status", status_plano_acao_enum, nullable=False),
        sa.Column("prazo", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["nao_conformidade_id"],
            ["certificacao_nao_conformidades.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["evidencia_id"], ["certificacao_evidencias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["responsavel_pessoa_id"],
            ["cadastros_pessoas.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["propriedade_id"], ["cadastros_propriedades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["imovel_rural_id"], ["imoveis_rurais.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["propriedade_imovel_id"],
            ["propriedade_imovel.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("btrim(titulo) <> ''", name="ck_certificacao_pa_titulo_nao_vazio"),
        sa.CheckConstraint(
            "concluido_em IS NULL OR concluido_em >= created_at",
            name="ck_certificacao_pa_conclusao_valida",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certificacao_planos_acao_tenant_id"),
        "certificacao_planos_acao",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_planos_acao_programa_id"),
        "certificacao_planos_acao",
        ["programa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_planos_acao_nao_conformidade_id"),
        "certificacao_planos_acao",
        ["nao_conformidade_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_planos_acao_evidencia_id"),
        "certificacao_planos_acao",
        ["evidencia_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_planos_acao_status"),
        "certificacao_planos_acao",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_planos_acao_prioridade"),
        "certificacao_planos_acao",
        ["prioridade"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_planos_acao_prazo"),
        "certificacao_planos_acao",
        ["prazo"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_pa_tenant_status",
        "certificacao_planos_acao",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_pa_tenant_prioridade",
        "certificacao_planos_acao",
        ["tenant_id", "prioridade"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_pa_tenant_prazo",
        "certificacao_planos_acao",
        ["tenant_id", "prazo"],
        unique=False,
    )
    _enable_tenant_rls("certificacao_planos_acao")


def downgrade() -> None:
    op.drop_table("certificacao_planos_acao")
    op.drop_table("certificacao_nao_conformidades")
    op.drop_table("certificacao_evidencias")

