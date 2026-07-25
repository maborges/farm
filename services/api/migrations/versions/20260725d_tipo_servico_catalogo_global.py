"""tipo_servico: tenant_id nullable + catalogo global de sugestoes

Mesmo padrao de Produto/Marca/CategoriaProduto: tenant_id NULL vira
catalogo global visivel a todos os tenants (soma-se ao que cada tenant
cadastra), servindo como sugestao inicial de servicos comumente
terceirizados. Registros globais sao somente leitura para o tenant
(bloqueado em service.py: atualizar/desativar).

Revision ID: 20260725d_tipo_servico_catalogo_global
Revises: 20260725c_backfill_cost_allocations
Create Date: 2026-07-25
"""
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20260725d_tipo_servico_catalogo_global"
down_revision = "20260725c_backfill_cost_allocations"
branch_labels = None
depends_on = None

CATALOGO_GLOBAL = [
    ("Aplicação terrestre (pulverização) terceirizada", "HA", None),
    ("Aplicação aérea (avião/drone) terceirizada", "HA", None),
    ("Colheita mecanizada terceirizada", "HA", None),
    ("Plantio terceirizado", "HA", None),
    ("Gradagem/preparo de solo terceirizado", "HA", None),
    ("Calagem/distribuição de calcário terceirizada", "HA", None),
    ("Adubação terceirizada", "HA", None),
    ("Transporte de grãos/insumos (frete terceirizado)", "KM", None),
    ("Colheita manual (turma terceirizada)", "DIA", None),
    ("Secagem/armazenagem terceirizada", "SC", None),
]


def upgrade():
    op.alter_column(
        "cadastros_tipos_servico",
        "tenant_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=True,
    )

    conn = op.get_bind()
    now = datetime.now(timezone.utc)
    tabela = sa.table(
        "cadastros_tipos_servico",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("tenant_id", sa.Uuid(as_uuid=True)),
        sa.column("nome", sa.String),
        sa.column("unidade_medida", sa.String),
        sa.column("custo_referencia", sa.Numeric),
        sa.column("observacoes", sa.Text),
        sa.column("ativo", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    conn.execute(
        tabela.insert(),
        [
            {
                "id": uuid.uuid4(),
                "tenant_id": None,
                "nome": nome,
                "unidade_medida": unidade,
                "custo_referencia": custo,
                "observacoes": None,
                "ativo": True,
                "created_at": now,
                "updated_at": now,
            }
            for nome, unidade, custo in CATALOGO_GLOBAL
        ],
    )
    op.execute("COMMIT")


def downgrade():
    op.execute("DELETE FROM cadastros_tipos_servico WHERE tenant_id IS NULL")
    op.alter_column(
        "cadastros_tipos_servico",
        "tenant_id",
        existing_type=sa.Uuid(as_uuid=True),
        nullable=False,
    )
    op.execute("COMMIT")
