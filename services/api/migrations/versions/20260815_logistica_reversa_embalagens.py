"""cria módulo de Logística Reversa de Embalagens (Lei 9.974/2000)

OPERATIONS-GAP-01 §21.16/§21.20: segunda e última fatia do gap de
compliance (a primeira foi o Receituário Agronômico, §21.19) — adiciona
`quantidade_embalagens` em ItemRecebimento (compras) e a tabela de
pendências de devolução `agricola_devolucoes_embalagens`, criadas
automaticamente no recebimento de compra de produto com
`requer_receituario=True`.

Revision ID: 20260815_logistica_reversa_embalagens
Revises: 20260815_receituario_agronomico
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_logistica_reversa_embalagens"
down_revision = "20260815_receituario_agronomico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "compras_recebimentos_itens",
        sa.Column("quantidade_embalagens", sa.Integer(), nullable=True),
    )

    op.create_table(
        "agricola_devolucoes_embalagens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("item_recebimento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compras_recebimentos_itens.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("produto_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_produtos.id"), nullable=False, index=True),
        sa.Column("quantidade_embalagens_compradas", sa.Integer(), nullable=False),
        sa.Column("quantidade_embalagens_devolvidas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_compra", sa.Date(), nullable=False),
        sa.Column("prazo_limite", sa.Date(), nullable=False),
        sa.Column("destino_pessoa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cadastros_pessoas.id"), nullable=True, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.Column("comprovante_pdf_url", sa.String(500), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_devolucao_embalagem_tenant_status_prazo",
        "agricola_devolucoes_embalagens",
        ["tenant_id", "status", "prazo_limite"],
    )
    op.execute("COMMIT")

    op.execute(
        """
        INSERT INTO cadastros_tipos_relacionamento
            (id, tenant_id, codigo, nome, descricao, cor, icone, sistema, ativo)
        SELECT gen_random_uuid(), NULL, 'POSTO_RECEBIMENTO', 'Posto de Recebimento',
               'Estabelecimento/revenda credenciado para devolução de embalagens de defensivos (Lei 9.974/2000)',
               '#0EA5E9', 'recycle', true, true
        WHERE NOT EXISTS (
            SELECT 1 FROM cadastros_tipos_relacionamento WHERE codigo = 'POSTO_RECEBIMENTO' AND tenant_id IS NULL
        )
        """
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.execute("DELETE FROM cadastros_tipos_relacionamento WHERE codigo = 'POSTO_RECEBIMENTO' AND tenant_id IS NULL")
    op.drop_table("agricola_devolucoes_embalagens")
    op.drop_column("compras_recebimentos_itens", "quantidade_embalagens")
    op.execute("COMMIT")
