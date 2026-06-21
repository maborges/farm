"""lote 1 - nucleos de certificacoes/esg

Revision ID: 20260621_certificacao_esg_lote1
Revises: add_propriedade_imovel
Create Date: 2026-06-21 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


# revision identifiers, used by Alembic.
revision = "20260621_certificacao_esg_lote1"
down_revision = "add_propriedade_imovel"
branch_labels = None
depends_on = None


status_programa_enum = PGEnum("ATIVO", "INATIVO", "SUSPENSO", name="status_programa_enum", create_type=False)
tipo_certificacao_enum = PGEnum(
    "ORGANICO",
    "GLOBALGAP",
    "REGENAGRI",
    "ESG_INTERNO",
    "OUTRO",
    name="tipo_certificacao_enum",
    create_type=False,
)
status_checklist_enum = PGEnum(
    "RASCUNHO",
    "PUBLICADO",
    "ARQUIVADO",
    name="status_checklist_enum",
    create_type=False,
)
resultado_avaliacao_enum = PGEnum(
    "APROVADO",
    "APROVADO_COM_RESSALVA",
    "REPROVADO",
    "PENDENTE",
    name="resultado_avaliacao_enum",
    create_type=False,
)
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
status_relatorio_esg_enum = PGEnum(
    "RASCUNHO",
    "EM_REVISAO",
    "PUBLICADO",
    "ARQUIVADO",
    name="status_relatorio_esg_enum",
    create_type=False,
)
status_passaporte_enum = PGEnum(
    "RASCUNHO",
    "ATIVO",
    "REVOGADO",
    name="status_passaporte_enum",
    create_type=False,
)


def _create_enum_types(bind) -> None:
    for enum_type in (
        status_programa_enum,
        tipo_certificacao_enum,
        status_checklist_enum,
        resultado_avaliacao_enum,
        tipo_evidencia_enum,
        severidade_nao_conformidade_enum,
        prioridade_plano_acao_enum,
        status_plano_acao_enum,
        status_relatorio_esg_enum,
        status_passaporte_enum,
    ):
        enum_type.create(bind, checkfirst=True)


def _drop_enum_types(bind) -> None:
    for enum_type in (
        status_passaporte_enum,
        status_relatorio_esg_enum,
        status_plano_acao_enum,
        prioridade_plano_acao_enum,
        severidade_nao_conformidade_enum,
        tipo_evidencia_enum,
        resultado_avaliacao_enum,
        status_checklist_enum,
        tipo_certificacao_enum,
        status_programa_enum,
    ):
        enum_type.drop(bind, checkfirst=True)


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
    _create_enum_types(bind)

    op.create_table(
        "certificacao_programas",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("propriedade_id", sa.UUID(), nullable=True),
        sa.Column("imovel_rural_id", sa.UUID(), nullable=True),
        sa.Column("propriedade_imovel_id", sa.UUID(), nullable=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("tipo_certificacao", tipo_certificacao_enum, nullable=False),
        sa.Column("status_programa", status_programa_enum, nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("organismo_certificador", sa.String(length=200), nullable=True),
        sa.Column("escopo", sa.Text(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["propriedade_id"],
            ["cadastros_propriedades.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["imovel_rural_id"],
            ["imoveis_rurais.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["propriedade_imovel_id"],
            ["propriedade_imovel.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "data_fim IS NULL OR data_fim >= data_inicio",
            name="ck_certificacao_programas_datas_validas",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certificacao_programas_tenant_id"),
        "certificacao_programas",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_programas_propriedade_id"),
        "certificacao_programas",
        ["propriedade_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_programas_imovel_rural_id"),
        "certificacao_programas",
        ["imovel_rural_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_programas_propriedade_imovel_id"),
        "certificacao_programas",
        ["propriedade_imovel_id"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_programas_tenant_status",
        "certificacao_programas",
        ["tenant_id", "status_programa"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_programas_tenant_tipo",
        "certificacao_programas",
        ["tenant_id", "tipo_certificacao"],
        unique=False,
    )
    _enable_tenant_rls("certificacao_programas")

    op.create_table(
        "certificacao_checklists",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("programa_certificacao_id", sa.UUID(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("norma_versao", sa.String(length=80), nullable=True),
        sa.Column("status_checklist", status_checklist_enum, nullable=False),
        sa.Column(
            "percentual_conformidade",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("data_abertura", sa.Date(), nullable=False),
        sa.Column("data_fechamento", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["programa_certificacao_id"],
            ["certificacao_programas.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "percentual_conformidade BETWEEN 0 AND 100",
            name="ck_certificacao_checklists_percentual_conformidade",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certificacao_checklists_tenant_id"),
        "certificacao_checklists",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_checklists_programa_certificacao_id"),
        "certificacao_checklists",
        ["programa_certificacao_id"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_checklists_tenant_status",
        "certificacao_checklists",
        ["tenant_id", "status_checklist"],
        unique=False,
    )
    _enable_tenant_rls("certificacao_checklists")

    op.create_table(
        "certificacao_criterios",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("checklist_certificacao_id", sa.UUID(), nullable=False),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("peso", sa.Numeric(10, 2), nullable=False),
        sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("observacoes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["checklist_certificacao_id"],
            ["certificacao_checklists.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("peso >= 0", name="ck_certificacao_criterios_peso_nao_negativo"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "checklist_certificacao_id",
            "codigo",
            name="uq_certificacao_criterios_codigo_por_checklist",
        ),
    )
    op.create_index(
        op.f("ix_certificacao_criterios_tenant_id"),
        "certificacao_criterios",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_criterios_checklist_certificacao_id"),
        "certificacao_criterios",
        ["checklist_certificacao_id"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_criterios_tenant_codigo",
        "certificacao_criterios",
        ["tenant_id", "codigo"],
        unique=False,
    )
    _enable_tenant_rls("certificacao_criterios")

    op.create_table(
        "certificacao_avaliacoes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("checklist_certificacao_id", sa.UUID(), nullable=False),
        sa.Column("avaliador_pessoa_id", sa.UUID(), nullable=False),
        sa.Column("resultado_avaliacao", resultado_avaliacao_enum, nullable=False),
        sa.Column("nota", sa.Numeric(10, 2), nullable=False),
        sa.Column("parecer", sa.Text(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["checklist_certificacao_id"],
            ["certificacao_checklists.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["avaliador_pessoa_id"],
            ["cadastros_pessoas.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("nota >= 0", name="ck_certificacao_avaliacoes_nota_nao_negativa"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certificacao_avaliacoes_tenant_id"),
        "certificacao_avaliacoes",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_avaliacoes_checklist_certificacao_id"),
        "certificacao_avaliacoes",
        ["checklist_certificacao_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificacao_avaliacoes_avaliador_pessoa_id"),
        "certificacao_avaliacoes",
        ["avaliador_pessoa_id"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_avaliacoes_tenant_resultado",
        "certificacao_avaliacoes",
        ["tenant_id", "resultado_avaliacao"],
        unique=False,
    )
    op.create_index(
        "ix_certificacao_avaliacoes_checklist_avaliador",
        "certificacao_avaliacoes",
        ["checklist_certificacao_id", "avaliador_pessoa_id"],
        unique=False,
    )
    _enable_tenant_rls("certificacao_avaliacoes")


def downgrade() -> None:
    op.drop_table("certificacao_avaliacoes")
    op.drop_table("certificacao_criterios")
    op.drop_table("certificacao_checklists")
    op.drop_table("certificacao_programas")

    bind = op.get_bind()
    _drop_enum_types(bind)
