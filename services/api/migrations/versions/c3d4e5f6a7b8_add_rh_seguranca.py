"""add rh seguranca

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-06-20 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rh_seguranca_itens",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("ca_numero", sa.String(length=50), nullable=True),
        sa.Column("validade_dias", sa.Integer(), nullable=True),
        sa.Column("fornecedor", sa.String(length=120), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rh_seguranca_itens_tenant_id"), "rh_seguranca_itens", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_rh_seguranca_itens_ca_numero"), "rh_seguranca_itens", ["ca_numero"], unique=False)

    op.create_table(
        "rh_seguranca_entregas",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("colaborador_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("item_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("unidade_produtiva_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("data_entrega", sa.Date(), nullable=False),
        sa.Column("data_validade", sa.Date(), nullable=True),
        sa.Column("quantidade", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ATIVA"),
        sa.Column("termo_assinado_url", sa.String(length=512), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("dados_extras", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["colaborador_id"], ["rh_colaboradores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["rh_seguranca_itens.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["unidades_produtivas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rh_seguranca_entregas_tenant_id"), "rh_seguranca_entregas", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_rh_seguranca_entregas_colaborador_id"), "rh_seguranca_entregas", ["colaborador_id"], unique=False)
    op.create_index(op.f("ix_rh_seguranca_entregas_item_id"), "rh_seguranca_entregas", ["item_id"], unique=False)
    op.create_index(op.f("ix_rh_seguranca_entregas_data_validade"), "rh_seguranca_entregas", ["data_validade"], unique=False)

    op.create_table(
        "rh_seguranca_documentos",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("colaborador_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("numero", sa.String(length=100), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=True),
        sa.Column("arquivo_url", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ATIVO"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["colaborador_id"], ["rh_colaboradores.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rh_seguranca_documentos_tenant_id"), "rh_seguranca_documentos", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_rh_seguranca_documentos_colaborador_id"), "rh_seguranca_documentos", ["colaborador_id"], unique=False)
    op.create_index(op.f("ix_rh_seguranca_documentos_data_vencimento"), "rh_seguranca_documentos", ["data_vencimento"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rh_seguranca_documentos_data_vencimento"), table_name="rh_seguranca_documentos")
    op.drop_index(op.f("ix_rh_seguranca_documentos_colaborador_id"), table_name="rh_seguranca_documentos")
    op.drop_index(op.f("ix_rh_seguranca_documentos_tenant_id"), table_name="rh_seguranca_documentos")
    op.drop_table("rh_seguranca_documentos")

    op.drop_index(op.f("ix_rh_seguranca_entregas_data_validade"), table_name="rh_seguranca_entregas")
    op.drop_index(op.f("ix_rh_seguranca_entregas_item_id"), table_name="rh_seguranca_entregas")
    op.drop_index(op.f("ix_rh_seguranca_entregas_colaborador_id"), table_name="rh_seguranca_entregas")
    op.drop_index(op.f("ix_rh_seguranca_entregas_tenant_id"), table_name="rh_seguranca_entregas")
    op.drop_table("rh_seguranca_entregas")

    op.drop_index(op.f("ix_rh_seguranca_itens_ca_numero"), table_name="rh_seguranca_itens")
    op.drop_index(op.f("ix_rh_seguranca_itens_tenant_id"), table_name="rh_seguranca_itens")
    op.drop_table("rh_seguranca_itens")
