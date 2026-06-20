"""add imoveis avaliacoes

Revision ID: b1c2d3e4f5a6
Revises: 43cdf769d080
Create Date: 2026-06-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "43cdf769d080"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "  CREATE TYPE metodoavaliacaoimovel AS ENUM ('MERCADO', 'CUSTO', 'RENDA', 'DECLARADO', 'LAUDO'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        )
    )

    op.create_table(
        "imoveis_avaliacoes",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("imovel_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("data_avaliacao", sa.DateTime(), nullable=False),
        sa.Column("metodo", sa.Enum("MERCADO", "CUSTO", "RENDA", "DECLARADO", "LAUDO", name="metodoavaliacaoimovel", create_type=False), nullable=False),
        sa.Column("valor_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("valor_por_hectare", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("valor_terra_nua", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("valor_benfeitorias", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("valor_lavoura_perene", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("moeda", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("responsavel", sa.String(length=200), nullable=True),
        sa.Column("numero_laudo", sa.String(length=100), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("anexos", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["imovel_id"], ["imoveis_rurais.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_imoveis_avaliacoes_tenant_id"), "imoveis_avaliacoes", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_imoveis_avaliacoes_imovel_id"), "imoveis_avaliacoes", ["imovel_id"], unique=False)
    op.create_index(op.f("ix_imoveis_avaliacoes_data_avaliacao"), "imoveis_avaliacoes", ["data_avaliacao"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_imoveis_avaliacoes_data_avaliacao"), table_name="imoveis_avaliacoes")
    op.drop_index(op.f("ix_imoveis_avaliacoes_imovel_id"), table_name="imoveis_avaliacoes")
    op.drop_index(op.f("ix_imoveis_avaliacoes_tenant_id"), table_name="imoveis_avaliacoes")
    op.drop_table("imoveis_avaliacoes")
    op.execute(sa.text("DROP TYPE IF EXISTS metodoavaliacaoimovel"))
