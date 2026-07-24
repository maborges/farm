"""Unifica Produto.tipo (enum solto, duplicado em Python e no frontend) com
CategoriaProduto (FK real, hierárquica, por tenant).

- Adiciona fin_planos_conta.categoria_produto_id (FK opcional para
  cadastros_categorias_produto) — permite a cada tenant vincular sua conta
  contábil à categoria de produto, substituindo o mapeamento fixo por
  Produto.tipo em ComprasService._resolver_plano_conta_compra.
- Semeia as 15 categorias-sistema (tenant_id NULL, sistema=True) equivalentes
  ao enum TipoProduto legado, para que produtos existentes ganhem
  categoria_id automaticamente sem perder a classificação atual.
- Backfill de cadastros_produtos.categoria_id a partir de tipo, só onde
  categoria_id ainda está NULL (não sobrescreve categorização já feita).

Revision ID: 20260723f_categoria_plano
Revises: 20260723e_ped_drop_legado
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260723f_categoria_plano"
down_revision = "20260723e_ped_drop_legado"
branch_labels = None
depends_on = None

# UUIDs fixos (determinísticos) para as categorias-sistema — permite backfill
# idempotente e referenciável em migrations futuras.
CATEGORIAS_SISTEMA = [
    ("11111111-ca70-0000-0000-000000000001", "SEMENTE", "Sementes"),
    ("11111111-ca70-0000-0000-000000000002", "DEFENSIVO", "Defensivos Agrícolas"),
    ("11111111-ca70-0000-0000-000000000003", "FERTILIZANTE", "Fertilizantes e Corretivos"),
    ("11111111-ca70-0000-0000-000000000004", "INOCULANTE", "Inoculantes"),
    ("11111111-ca70-0000-0000-000000000005", "ADJUVANTE", "Adjuvantes"),
    ("11111111-ca70-0000-0000-000000000006", "RACAO", "Ração"),
    ("11111111-ca70-0000-0000-000000000007", "MEDICAMENTO", "Medicamentos Veterinários"),
    ("11111111-ca70-0000-0000-000000000008", "VACINA", "Vacinas"),
    ("11111111-ca70-0000-0000-000000000009", "MINERAL", "Sal Mineral e Suplementos"),
    ("11111111-ca70-0000-0000-000000000010", "PECA", "Peças de Máquinas"),
    ("11111111-ca70-0000-0000-000000000011", "LUBRIFICANTE", "Lubrificantes"),
    ("11111111-ca70-0000-0000-000000000012", "COMBUSTIVEL", "Combustíveis"),
    ("11111111-ca70-0000-0000-000000000013", "MATERIAL_GERAL", "Materiais de Uso Geral"),
    ("11111111-ca70-0000-0000-000000000014", "EPI", "Equipamentos de Proteção Individual"),
    ("11111111-ca70-0000-0000-000000000015", "SERVICO", "Serviços Contratados"),
]


def upgrade():
    op.add_column(
        "fin_planos_conta",
        sa.Column("categoria_produto_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_planoconta_categoria_produto",
        "fin_planos_conta",
        "cadastros_categorias_produto",
        ["categoria_produto_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_fin_planos_conta_categoria_produto_id",
        "fin_planos_conta",
        ["categoria_produto_id"],
    )

    conn = op.get_bind()
    for cat_id, tipo, nome in CATEGORIAS_SISTEMA:
        conn.execute(
            sa.text(
                """
                INSERT INTO cadastros_categorias_produto
                    (id, tenant_id, sistema, parent_id, nome, ordem, ativo, created_at, updated_at)
                SELECT :id, NULL, true, NULL, :nome, 0, true, now(), now()
                WHERE NOT EXISTS (
                    SELECT 1 FROM cadastros_categorias_produto WHERE id = :id
                )
                """
            ),
            {"id": cat_id, "nome": nome},
        )
        conn.execute(
            sa.text(
                """
                UPDATE cadastros_produtos
                SET categoria_id = :id
                WHERE categoria_id IS NULL AND tipo = :tipo
                """
            ),
            {"id": cat_id, "tipo": tipo},
        )

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_fin_planos_conta_categoria_produto_id", table_name="fin_planos_conta")
    op.drop_constraint("fk_planoconta_categoria_produto", "fin_planos_conta", type_="foreignkey")
    op.drop_column("fin_planos_conta", "categoria_produto_id")
    op.execute("COMMIT")
