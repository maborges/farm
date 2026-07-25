"""Item de orçamento passa a suportar origem em cadastro mestre com snapshot imutável.

- Adiciona origem_tipo (PRODUTO/MAQUINA/PESSOA/SERVICO/MANUAL) e origem_id (sem FK,
  mesmo padrão híbrido de CostAllocation.source/source_id) para registrar de onde
  veio o custo unitário do item de orçamento.
- custo_unitario_snapshot congela o valor lido do cadastro mestre no momento da
  captura; custo_unitario_ajustado permite override manual no orçamento sem jamais
  escrever de volta no cadastro mestre; snapshot_data guarda o registro de origem
  bruto para auditoria mesmo que o cadastro mude ou seja removido depois.
- Itens existentes ficam com origem_tipo=MANUAL (comportamento atual preservado).

Revision ID: 20260725a_orc_snapshot
Revises: 20260724c_colab_pessoa
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260725a_orc_snapshot"
down_revision = "20260724c_colab_pessoa"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "agricola_orcamento_itens",
        sa.Column("origem_tipo", sa.String(20), nullable=False, server_default="MANUAL"),
    )
    op.add_column(
        "agricola_orcamento_itens",
        sa.Column("origem_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "agricola_orcamento_itens",
        sa.Column("custo_unitario_snapshot", sa.Numeric(14, 4), nullable=True),
    )
    op.add_column(
        "agricola_orcamento_itens",
        sa.Column("custo_unitario_ajustado", sa.Numeric(14, 4), nullable=True),
    )
    op.add_column(
        "agricola_orcamento_itens",
        sa.Column("snapshot_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "agricola_orcamento_itens",
        sa.Column("capturado_em", sa.DateTime(timezone=True), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE agricola_orcamento_itens SET origem_tipo = 'MANUAL' WHERE origem_tipo IS NULL"
    ))

    op.create_index(
        "ix_agricola_orcamento_itens_origem",
        "agricola_orcamento_itens",
        ["origem_tipo", "origem_id"],
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_agricola_orcamento_itens_origem", table_name="agricola_orcamento_itens")
    op.drop_column("agricola_orcamento_itens", "capturado_em")
    op.drop_column("agricola_orcamento_itens", "snapshot_data")
    op.drop_column("agricola_orcamento_itens", "custo_unitario_ajustado")
    op.drop_column("agricola_orcamento_itens", "custo_unitario_snapshot")
    op.drop_column("agricola_orcamento_itens", "origem_id")
    op.drop_column("agricola_orcamento_itens", "origem_tipo")
