"""cadastro tipo_servico — origem de custo SERVICO no orcamento de safra

Cria core/cadastros/tipos_servico como cadastro mestre, análogo a
Produto/Equipamento/ColaboradorRH, para permitir que SnapshotCustoService
resolva origem_tipo=SERVICO sem depender de custo_unitario manual.

Revision ID: 20260725b_tipo_servico
Revises: 20260725a_orc_snapshot
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260725b_tipo_servico"
down_revision = "20260725a_orc_snapshot"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cadastros_tipos_servico",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("unidade_medida", sa.String(20), nullable=False, server_default="UN"),
        sa.Column("custo_referencia", sa.Numeric(14, 4), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cadastros_tipos_servico_tenant_id", "cadastros_tipos_servico", ["tenant_id"])
    op.create_index("ix_cadastros_tipos_servico_nome", "cadastros_tipos_servico", ["nome"])
    op.create_index("ix_cadastros_tipos_servico_tenant_nome", "cadastros_tipos_servico", ["tenant_id", "nome"])
    op.execute("COMMIT")


def downgrade():
    op.drop_table("cadastros_tipos_servico")
    op.execute("COMMIT")
