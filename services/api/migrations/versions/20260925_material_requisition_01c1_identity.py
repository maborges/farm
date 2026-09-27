"""MATERIAL-REQUISITION-FLOW-01C1: identidade operacional contextual.

Cria o menor vínculo canônico entre a conta autenticada (Usuario) e a Pessoa
operacional no contexto do Tenant. Não realiza backfill por e-mail, CPF ou
nome e não altera o workflow de entrega/recebimento.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260925_material_requisition_01c1"
down_revision: str | Sequence[str] | None = "20260924_material_requisition_01c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE = "cadastros_pessoas_usuarios"


def _install_rls() -> None:
    expression = "tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), '')"
    op.execute(sa.text(f"ALTER TABLE farms.{TABLE} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE farms.{TABLE} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"CREATE POLICY pessoa_usuario_select_tenant ON farms.{TABLE} "
            f"FOR SELECT USING ({expression})"
        )
    )
    op.execute(
        sa.text(
            f"CREATE POLICY pessoa_usuario_insert_tenant ON farms.{TABLE} "
            f"FOR INSERT WITH CHECK ({expression})"
        )
    )
    op.execute(
        sa.text(
            f"CREATE POLICY pessoa_usuario_update_tenant ON farms.{TABLE} "
            f"FOR UPDATE USING ({expression}) WITH CHECK ({expression})"
        )
    )
    op.execute(
        sa.text(
            f"CREATE POLICY pessoa_usuario_delete_tenant ON farms.{TABLE} "
            f"FOR DELETE USING ({expression})"
        )
    )


def _drop_rls() -> None:
    for action in ("select", "insert", "update", "delete"):
        op.execute(
            f"DROP POLICY IF EXISTS pessoa_usuario_{action}_tenant ON farms.{TABLE}"
        )
    op.execute(f"ALTER TABLE farms.{TABLE} NO FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    # Required for a tenant-safe FK from the identity relation to the user's
    # contextual membership. Existing data was checked before this migration.
    op.create_unique_constraint(
        "uq_tenant_usuarios_tenant_usuario",
        "tenant_usuarios",
        ["tenant_id", "usuario_id"],
    )

    # 01C introduced tenant_id on requisition items but only created the
    # composite request FK. Complete the direct tenant guardrail here without
    # editing the already-applied 01C migration.
    op.create_foreign_key(
        "fk_estoque_requisicoes_itens_tenant",
        "estoque_requisicoes_itens",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 01C's new tenant FKs used CASCADE; normalize those newly introduced
    # guardrails before authorizing the next phase.
    for table_name, old_name, new_name in (
        (
            "estoque_requisicao_item_eventos",
            "estoque_requisicao_item_eventos_tenant_id_fkey",
            "fk_req_item_evento_tenant",
        ),
        (
            "estoque_requisicao_responsabilidades",
            "estoque_requisicao_responsabilidades_tenant_id_fkey",
            "fk_req_responsabilidade_tenant",
        ),
    ):
        op.drop_constraint(old_name, table_name, type_="foreignkey")
        op.create_foreign_key(
            new_name,
            table_name,
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_table(
        TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("pessoa_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ATIVO"),
        sa.Column(
            "vigencia_inicio",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("vigencia_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vinculado_por_usuario_id", sa.Uuid(), nullable=True),
        sa.Column("revogado_por_usuario_id", sa.Uuid(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "pessoa_id"],
            ["cadastros_pessoas.tenant_id", "cadastros_pessoas.id"],
            name="fk_pessoa_usuario_tenant_pessoa",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "usuario_id"],
            ["tenant_usuarios.tenant_id", "tenant_usuarios.usuario_id"],
            name="fk_pessoa_usuario_tenant_usuario",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["vinculado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["revogado_por_usuario_id"], ["usuarios.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_pessoa_usuario_tenant_id"),
        sa.CheckConstraint(
            "status IN ('ATIVO','REVOGADO')", name="ck_pessoa_usuario_status"
        ),
        sa.CheckConstraint(
            "vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio",
            name="ck_pessoa_usuario_vigencia",
        ),
    )
    op.create_index("ix_pessoa_usuario_tenant", TABLE, ["tenant_id"])
    op.create_index("ix_pessoa_usuario_pessoa", TABLE, ["tenant_id", "pessoa_id"])
    op.create_index("ix_pessoa_usuario_usuario", TABLE, ["tenant_id", "usuario_id"])
    op.create_index(
        "uq_pessoa_usuario_tenant_pessoa_ativo",
        TABLE,
        ["tenant_id", "pessoa_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ATIVO'"),
    )
    op.create_index(
        "uq_pessoa_usuario_tenant_usuario_ativo",
        TABLE,
        ["tenant_id", "usuario_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ATIVO'"),
    )
    op.create_index(
        "ix_pessoa_usuario_tenant_vigencia",
        TABLE,
        ["tenant_id", "usuario_id", "vigencia_fim"],
    )

    op.add_column(
        "estoque_requisicao_responsabilidades",
        sa.Column("pessoa_usuario_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_req_responsabilidade_pessoa_usuario",
        "estoque_requisicao_responsabilidades",
        ["tenant_id", "pessoa_usuario_id"],
    )
    op.create_foreign_key(
        "fk_req_responsabilidade_tenant_pessoa_usuario",
        "estoque_requisicao_responsabilidades",
        TABLE,
        ["tenant_id", "pessoa_usuario_id"],
        ["tenant_id", "id"],
        ondelete="NO ACTION",
    )
    _install_rls()


def downgrade() -> None:
    _drop_rls()
    op.execute(
        "ALTER TABLE farms.estoque_requisicao_responsabilidades "
        "DROP CONSTRAINT IF EXISTS fk_req_responsabilidade_tenant"
    )
    op.execute(
        "ALTER TABLE farms.estoque_requisicao_responsabilidades "
        "DROP CONSTRAINT IF EXISTS estoque_requisicao_responsabilidades_tenant_id_fkey"
    )
    op.create_foreign_key(
        "estoque_requisicao_responsabilidades_tenant_id_fkey",
        "estoque_requisicao_responsabilidades",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        "ALTER TABLE farms.estoque_requisicao_item_eventos "
        "DROP CONSTRAINT IF EXISTS fk_req_item_evento_tenant"
    )
    op.execute(
        "ALTER TABLE farms.estoque_requisicao_item_eventos "
        "DROP CONSTRAINT IF EXISTS estoque_requisicao_item_eventos_tenant_id_fkey"
    )
    op.create_foreign_key(
        "estoque_requisicao_item_eventos_tenant_id_fkey",
        "estoque_requisicao_item_eventos",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_req_responsabilidade_tenant_pessoa_usuario",
        "estoque_requisicao_responsabilidades",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_req_responsabilidade_pessoa_usuario",
        table_name="estoque_requisicao_responsabilidades",
    )
    op.drop_column("estoque_requisicao_responsabilidades", "pessoa_usuario_id")
    op.execute(
        "ALTER TABLE farms.estoque_requisicoes_itens "
        "DROP CONSTRAINT IF EXISTS fk_estoque_requisicoes_itens_tenant"
    )
    for index_name in (
        "ix_pessoa_usuario_tenant_vigencia",
        "uq_pessoa_usuario_tenant_usuario_ativo",
        "uq_pessoa_usuario_tenant_pessoa_ativo",
        "ix_pessoa_usuario_usuario",
        "ix_pessoa_usuario_pessoa",
        "ix_pessoa_usuario_tenant",
    ):
        op.drop_index(index_name, table_name=TABLE)
    op.drop_table(TABLE)
    op.drop_constraint(
        "uq_tenant_usuarios_tenant_usuario", "tenant_usuarios", type_="unique"
    )
