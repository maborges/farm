"""cria módulo de Receituário Agronômico (CREA)

OPERATIONS-GAP-01 §21.16/§21.19: fecha o gap de ausência total de
Receituário Agronômico (Lei 7.802/1989) — cria cadastro de perfil profissional
CREA em Pessoa (extensão 1:1, mesmo padrão de ProdutoAgricola), o documento
ReceituarioAgronomico + itens, e semeia o TipoRelacionamento código AGRONOMO.

Revision ID: 20260815_receituario_agronomico
Revises: 20260815_cost_alloc_src_frota_rh
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_receituario_agronomico"
down_revision = "20260815_cost_alloc_src_frota_rh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cadastros_pessoas_profissional_agronomo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("pessoa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_pessoas.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("crea_numero", sa.String(30), nullable=False),
        sa.Column("crea_uf", sa.String(2), nullable=False),
        sa.Column("crea_validade", sa.Date(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "agricola_receituarios_agronomicos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("numero", sa.String(50), nullable=True),
        sa.Column("agronomo_pessoa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_pessoas.id"), nullable=False, index=True),
        sa.Column("crea_numero", sa.String(30), nullable=False),
        sa.Column("crea_uf", sa.String(2), nullable=False),
        sa.Column("unidade_produtiva_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("unidades_produtivas.id"), nullable=False, index=True),
        sa.Column("safra_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("talhao_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operacao_agricola_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("cultura", sa.String(50), nullable=True),
        sa.Column("praga_alvo", sa.String(100), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("data_validade", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RASCUNHO"),
        sa.Column("arquivo_pdf_url", sa.String(500), nullable=True),
        sa.Column("arquivo_pdf_tamanho_bytes", sa.Integer(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_receituario_tenant_status_validade",
        "agricola_receituarios_agronomicos",
        ["tenant_id", "status", "data_validade"],
    )

    op.create_table(
        "agricola_receituario_itens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("receituario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agricola_receituarios_agronomicos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("produto_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_produtos.id"), nullable=False, index=True),
        sa.Column("dose", sa.Numeric(10, 4), nullable=False),
        sa.Column("unidade_dose", sa.String(20), nullable=False),
        sa.Column("cultura", sa.String(50), nullable=True),
        sa.Column("praga_alvo", sa.String(100), nullable=True),
        sa.Column("carencia_dias", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_receituario_itens_produto",
        "agricola_receituario_itens",
        ["tenant_id", "produto_id"],
    )
    op.add_column(
        "caderno_campo_entradas",
        sa.Column(
            "receituario_agronomico_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agricola_receituarios_agronomicos.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_caderno_campo_entradas_receituario_agronomico_id",
        "caderno_campo_entradas",
        ["receituario_agronomico_id"],
    )
    op.execute("COMMIT")

    op.execute(
        """
        INSERT INTO cadastros_tipos_relacionamento
            (id, tenant_id, codigo, nome, descricao, cor, icone, sistema, ativo)
        SELECT gen_random_uuid(), NULL, 'AGRONOMO', 'Agrônomo',
               'Engenheiro agrônomo responsável técnico (CREA) por Receituários Agronômicos',
               '#16A34A', 'sprout', true, true
        WHERE NOT EXISTS (
            SELECT 1 FROM cadastros_tipos_relacionamento WHERE codigo = 'AGRONOMO' AND tenant_id IS NULL
        )
        """
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.execute("DELETE FROM cadastros_tipos_relacionamento WHERE codigo = 'AGRONOMO' AND tenant_id IS NULL")
    op.drop_index("ix_caderno_campo_entradas_receituario_agronomico_id", table_name="caderno_campo_entradas")
    op.drop_column("caderno_campo_entradas", "receituario_agronomico_id")
    op.drop_table("agricola_receituario_itens")
    op.drop_table("agricola_receituarios_agronomicos")
    op.drop_table("cadastros_pessoas_profissional_agronomo")
    op.execute("COMMIT")
