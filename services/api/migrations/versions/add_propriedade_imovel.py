"""add_propriedade_imovel

Revision ID: add_propriedade_imovel
Revises: merge_heads_before_propriedade_imovel
Create Date: 2026-06-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_propriedade_imovel"
down_revision: Union[str, Sequence[str], None] = "merge_heads_before_propriedade_imovel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "propriedade_imovel"
TIPOS_VINCULO = (
    "PROPRIEDADE_PRINCIPAL",
    "PROPRIEDADE_SECUNDARIA",
    "ARRENDAMENTO",
    "PARCERIA_RURAL",
    "COMODATO",
    "USO_COMPARTILHADO",
    "USO_TEMPORARIO",
    "INTEGRACAO",
    "OUTRO",
)


def upgrade() -> None:
    op.create_table(
        TABELA,
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False, comment="Identificador do vínculo canônico."),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False, comment="Tenant dono do vínculo."),
        sa.Column(
            "propriedade_id",
            sa.Uuid(as_uuid=True),
            nullable=False,
            comment="Referência à propriedade operacional vinculada.",
        ),
        sa.Column(
            "imovel_rural_id",
            sa.Uuid(as_uuid=True),
            nullable=False,
            comment="Referência ao imóvel rural fundiário/documental vinculado.",
        ),
        sa.Column(
            "tipo_vinculo",
            sa.String(length=40),
            nullable=False,
            comment="Classificação textual do tipo de vínculo entre os domínios.",
        ),
        sa.Column(
            "ativo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Indica se o vínculo está vigente.",
        ),
        sa.Column(
            "data_inicio",
            sa.Date(),
            nullable=False,
            comment="Início da vigência do vínculo.",
        ),
        sa.Column(
            "data_fim",
            sa.Date(),
            nullable=True,
            comment="Fim da vigência do vínculo, quando encerrado.",
        ),
        sa.Column(
            "origem_documental",
            sa.Text(),
            nullable=False,
            comment="Base documental que justifica o vínculo.",
        ),
        sa.Column(
            "observacoes",
            sa.Text(),
            nullable=True,
            comment="Observações livres sobre o vínculo.",
        ),
        sa.Column(
            "area_vinculada",
            sa.Numeric(precision=14, scale=4),
            nullable=True,
            comment="Área vinculada no contexto do vínculo.",
        ),
        sa.Column(
            "percentual_vinculado",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
            comment="Percentual da área vinculada em relação ao domínio de origem.",
        ),
        sa.Column(
            "vinculo_principal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Marca o vínculo principal da propriedade em relação ao imóvel rural.",
        ),
        sa.Column(
            "origem_referencia",
            sa.Text(),
            nullable=True,
            comment="Referência complementar da origem documental.",
        ),
        sa.Column(
            "status_documental",
            sa.String(length=30),
            nullable=True,
            comment="Situação documental associada ao vínculo.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Data de criação do vínculo.",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Data da última atualização do vínculo.",
        ),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            nullable=True,
            comment="Usuário que criou o vínculo.",
        ),
        sa.Column(
            "updated_by",
            sa.Uuid(as_uuid=True),
            nullable=True,
            comment="Usuário que atualizou o vínculo por último.",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["propriedade_id"], ["cadastros_propriedades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["imovel_rural_id"], ["imoveis_rurais.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "tipo_vinculo IN ('PROPRIEDADE_PRINCIPAL', 'PROPRIEDADE_SECUNDARIA', 'ARRENDAMENTO', 'PARCERIA_RURAL', 'COMODATO', 'USO_COMPARTILHADO', 'USO_TEMPORARIO', 'INTEGRACAO', 'OUTRO')",
            name="ck_propriedade_imovel_tipo_vinculo",
        ),
        sa.CheckConstraint(
            "data_fim IS NULL OR data_fim >= data_inicio",
            name="ck_propriedade_imovel_datas_validas",
        ),
        sa.CheckConstraint(
            "percentual_vinculado IS NULL OR (percentual_vinculado >= 0 AND percentual_vinculado <= 100)",
            name="ck_propriedade_imovel_percentual_intervalo",
        ),
        sa.CheckConstraint(
            "area_vinculada IS NULL OR area_vinculada >= 0",
            name="ck_propriedade_imovel_area_nao_negativa",
        ),
        comment=(
            "Tabela canônica de vínculo entre Propriedades e Imóveis Rurais. "
            "Guarda apenas o vínculo e sua vigência, para rastreabilidade, ESG e Projeto Raízes."
        ),
    )

    op.create_index(
        "ix_propriedade_imovel_tenant_id",
        TABELA,
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_propriedade_id",
        TABELA,
        ["propriedade_id"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_imovel_rural_id",
        TABELA,
        ["imovel_rural_id"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_tenant_propriedade",
        TABELA,
        ["tenant_id", "propriedade_id"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_tenant_imovel_rural",
        TABELA,
        ["tenant_id", "imovel_rural_id"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_tipo_vinculo",
        TABELA,
        ["tipo_vinculo"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_ativo",
        TABELA,
        ["ativo"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_data_inicio",
        TABELA,
        ["data_inicio"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_data_fim",
        TABELA,
        ["data_fim"],
        unique=False,
    )
    op.create_index(
        "ix_propriedade_imovel_vinculo_principal",
        TABELA,
        ["vinculo_principal"],
        unique=False,
    )
    op.create_index(
        "uq_propriedade_imovel_principal_ativo",
        TABELA,
        ["tenant_id", "propriedade_id"],
        unique=True,
        postgresql_where=sa.text("vinculo_principal IS TRUE AND ativo IS TRUE AND data_fim IS NULL"),
    )

    op.execute(sa.text(f"ALTER TABLE {TABELA} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {TABELA} FORCE ROW LEVEL SECURITY"))

    op.execute(
        sa.text(
            f"""
            CREATE POLICY propriedade_imovel_select_policy
            ON {TABELA}
            FOR SELECT
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY propriedade_imovel_insert_policy
            ON {TABELA}
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY propriedade_imovel_update_policy
            ON {TABELA}
            FOR UPDATE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY propriedade_imovel_delete_policy
            ON {TABELA}
            FOR DELETE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text(f"DROP POLICY IF EXISTS propriedade_imovel_delete_policy ON {TABELA}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS propriedade_imovel_update_policy ON {TABELA}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS propriedade_imovel_insert_policy ON {TABELA}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS propriedade_imovel_select_policy ON {TABELA}"))
    op.execute(sa.text(f"ALTER TABLE {TABELA} DISABLE ROW LEVEL SECURITY"))

    op.drop_index("uq_propriedade_imovel_principal_ativo", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_vinculo_principal", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_data_fim", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_data_inicio", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_ativo", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_tipo_vinculo", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_tenant_imovel_rural", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_tenant_propriedade", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_imovel_rural_id", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_propriedade_id", table_name=TABELA)
    op.drop_index("ix_propriedade_imovel_tenant_id", table_name=TABELA)

    op.drop_table(TABELA)
