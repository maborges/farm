"""generaliza beneficiamento pós-colheita (extrai campos de café p/ extensão)

OPERATIONS-GAP-01 §21.15/§21.21: `cafe_lotes_beneficiamento` era acoplado a
café (nomenclatura ABIC/SCA). Renomeia para `agricola_lotes_beneficiamento`
(genérico) e extrai os campos específicos de café (método, peneira, bebida,
pontuação SCA, defeitos, local de secagem) para a tabela de extensão 1:1
`cafe_lote_beneficiamento_detalhes`. Usuário confirmou que os dados atuais
podem ser truncados — sem backfill, rename + restructure direto.

Revision ID: 20260815_beneficiamento_generico
Revises: 20260815_logistica_reversa_embalagens
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_beneficiamento_generico"
down_revision = "20260815_logistica_reversa_embalagens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("TRUNCATE TABLE cafe_lote_beneficiamento_romaneios, cafe_lotes_beneficiamento CASCADE")

    op.rename_table("cafe_lotes_beneficiamento", "agricola_lotes_beneficiamento")

    for coluna in (
        "metodo", "local_secagem", "peneira_principal", "bebida",
        "pontuacao_scaa", "defeitos_intrinsecos", "defeitos_extrinsecos",
    ):
        op.drop_column("agricola_lotes_beneficiamento", coluna)

    op.add_column(
        "agricola_lotes_beneficiamento",
        sa.Column("fator_esperado_manual", sa.Numeric(6, 3), nullable=True),
    )

    op.create_table(
        "cafe_lote_beneficiamento_detalhes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("lote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agricola_lotes_beneficiamento.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("metodo", sa.String(20), nullable=False),
        sa.Column("local_secagem", sa.String(30), nullable=True),
        sa.Column("peneira_principal", sa.String(10), nullable=True),
        sa.Column("bebida", sa.String(30), nullable=True),
        sa.Column("pontuacao_scaa", sa.Numeric(4, 2), nullable=True),
        sa.Column("defeitos_intrinsecos", sa.Integer(), nullable=True),
        sa.Column("defeitos_extrinsecos", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.execute("TRUNCATE TABLE cafe_lote_beneficiamento_romaneios, agricola_lotes_beneficiamento CASCADE")
    op.drop_table("cafe_lote_beneficiamento_detalhes")

    op.add_column("agricola_lotes_beneficiamento", sa.Column("metodo", sa.String(20), nullable=True))
    op.add_column("agricola_lotes_beneficiamento", sa.Column("local_secagem", sa.String(30), nullable=True))
    op.add_column("agricola_lotes_beneficiamento", sa.Column("peneira_principal", sa.String(10), nullable=True))
    op.add_column("agricola_lotes_beneficiamento", sa.Column("bebida", sa.String(30), nullable=True))
    op.add_column("agricola_lotes_beneficiamento", sa.Column("pontuacao_scaa", sa.Numeric(4, 2), nullable=True))
    op.add_column("agricola_lotes_beneficiamento", sa.Column("defeitos_intrinsecos", sa.Integer(), nullable=True))
    op.add_column("agricola_lotes_beneficiamento", sa.Column("defeitos_extrinsecos", sa.Integer(), nullable=True))
    op.drop_column("agricola_lotes_beneficiamento", "fator_esperado_manual")

    op.rename_table("agricola_lotes_beneficiamento", "cafe_lotes_beneficiamento")
    op.execute("COMMIT")
