"""Fase 2 do PLANO-OPERACIONAL-01: necessidade agronômica estruturada e grupo de geração.

Adiciona `grupo_geracao_id` (nullable, imutável) em `safra_tarefas` para marcar
tarefas nascidas juntas na mesma ação de geração em lote (ex.: gerar tarefas para
vários talhões a partir de análises de solo). Cria `safra_tarefa_necessidades`
para representar tecnicamente o que a tarefa precisa (categoria/dose/quantidade),
antes da escolha do produto comercial — que continua sendo feita depois, na
geração da OS (`PlanejarOperacaoRequest.insumos`) ou no Planejamento Operacional
(fases seguintes). Ambas as mudanças são aditivas: tarefas existentes ficam com
`grupo_geracao_id=NULL` (correto — não tiveram geração em lote) e nenhuma
necessidade retroativa é criada nesta migration.

Revision ID: 20260726b_tarefa_necessidade_grupo
Revises: 20260726a_plano_operacional
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260726b_tarefa_necessidade_grupo"
down_revision = "20260726a_plano_operacional"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "safra_tarefas",
        sa.Column("grupo_geracao_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_safra_tarefas_grupo_geracao", "safra_tarefas", ["grupo_geracao_id"])

    op.create_table(
        "safra_tarefa_necessidades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_tarefa_id", UUID(as_uuid=True), sa.ForeignKey("safra_tarefas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("categoria", sa.String(20), nullable=False),
        sa.Column("tipo_aplicacao", sa.String(50), nullable=True),
        sa.Column("unidade_referencia", sa.String(20), nullable=False),
        sa.Column("dose_tecnica", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantidade_tecnica", sa.Numeric(14, 2), nullable=True),
        sa.Column("area_referencia_ha", sa.Numeric(10, 2), nullable=True),
        sa.Column("origem_calculo", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("parametros_calculo", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_safra_tarefa_necessidades_tenant_id", "safra_tarefa_necessidades", ["tenant_id"])
    op.create_index("ix_safra_tarefa_necessidades_safra_tarefa_id", "safra_tarefa_necessidades", ["safra_tarefa_id"])
    op.create_index(
        "ix_safra_tarefa_necessidades_tenant_tarefa",
        "safra_tarefa_necessidades",
        ["tenant_id", "safra_tarefa_id"],
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_safra_tarefa_necessidades_tenant_tarefa", table_name="safra_tarefa_necessidades")
    op.drop_index("ix_safra_tarefa_necessidades_safra_tarefa_id", table_name="safra_tarefa_necessidades")
    op.drop_index("ix_safra_tarefa_necessidades_tenant_id", table_name="safra_tarefa_necessidades")
    op.drop_table("safra_tarefa_necessidades")

    op.drop_index("ix_safra_tarefas_grupo_geracao", table_name="safra_tarefas")
    op.drop_column("safra_tarefas", "grupo_geracao_id")

    op.execute("COMMIT")
