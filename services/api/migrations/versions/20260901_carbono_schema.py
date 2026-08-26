"""Create the carbon tables expected by the current Ambiental API."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260901_carbono_schema"
down_revision = "20260901_balanca_contingency"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    """Return whether a table exists in the current PostgreSQL schema."""
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    """Create missing carbon tables using the current ORM contract."""
    if not _table_exists("carbono_emissoes"):
        op.create_table(
            "carbono_emissoes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(50), nullable=False),
            sa.Column("unidade_produtiva_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("escopo", sa.Integer(), nullable=False),
            sa.Column("categoria", sa.String(100), nullable=False),
            sa.Column("fonte", sa.String(200)),
            sa.Column("atividade", sa.String(200)),
            sa.Column("quantidade", sa.Float(), nullable=False),
            sa.Column("unidade", sa.String(50), nullable=False),
            sa.Column("fator_emissao", sa.Float()),
            sa.Column("fator_emissao_referencia", sa.String(200)),
            sa.Column("total_co2e", sa.Float()),
            sa.Column("data_referencia", sa.DateTime(), nullable=False),
            sa.Column("observacoes", sa.Text()),
            sa.Column("arquivo_comprovante", sa.String(500)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("created_by", postgresql.UUID(as_uuid=True)),
            sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["production_units.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"]),
        )
        op.create_index("ix_carbono_emissoes_id", "carbono_emissoes", ["id"])
        op.create_index("ix_carbono_emissoes_tenant_id", "carbono_emissoes", ["tenant_id"])

    if not _table_exists("carbono_projetos"):
        op.create_table(
            "carbono_projetos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(50), nullable=False),
            sa.Column("unidade_produtiva_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("nome", sa.String(200), nullable=False),
            sa.Column("descricao", sa.Text()),
            sa.Column("tipo", sa.String(50), nullable=False),
            sa.Column("metodologia", sa.String(100)),
            sa.Column("area_ha", sa.Float(), nullable=False),
            sa.Column("geometria", postgresql.JSONB(astext_type=sa.Text())),
            sa.Column("creditos_estimados", sa.Float()),
            sa.Column("creditos_verificados", sa.Float()),
            sa.Column("creditos_vendidos", sa.Float()),
            sa.Column("status", sa.String(50)),
            sa.Column("data_inicio", sa.Date()),
            sa.Column("data_verificacao", sa.Date()),
            sa.Column("data_certificacao", sa.Date()),
            sa.Column("certificador", sa.String(200)),
            sa.Column("numero_registro", sa.String(100)),
            sa.Column("padrao", sa.String(50)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
            sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["production_units.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_carbono_projetos_id", "carbono_projetos", ["id"])
        op.create_index("ix_carbono_projetos_tenant_id", "carbono_projetos", ["tenant_id"])

    if not _table_exists("carbono_relatorios"):
        op.create_table(
            "carbono_relatorios",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(50), nullable=False),
            sa.Column("periodo_inicio", sa.DateTime(), nullable=False),
            sa.Column("periodo_fim", sa.DateTime(), nullable=False),
            sa.Column("escopo_1_total", sa.Float()),
            sa.Column("escopo_2_total", sa.Float()),
            sa.Column("escopo_3_total", sa.Float()),
            sa.Column("total_geral", sa.Float()),
            sa.Column("creditos_gerados", sa.Float()),
            sa.Column("saldo_liquido", sa.Float()),
            sa.Column("intensidade_carbono", sa.Float()),
            sa.Column("unidade_producao", sa.String(50)),
            sa.Column("total_produzido", sa.Float()),
            sa.Column("status", sa.String(50)),
            sa.Column("arquivo_pdf", sa.String(500)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("published_at", sa.DateTime()),
        )
        op.create_index("ix_carbono_relatorios_id", "carbono_relatorios", ["id"])
        op.create_index("ix_carbono_relatorios_tenant_id", "carbono_relatorios", ["tenant_id"])


def downgrade() -> None:
    """Remove only tables created by this repair migration."""
    for table in ("carbono_relatorios", "carbono_projetos", "carbono_emissoes"):
        if _table_exists(table):
            op.drop_table(table)
