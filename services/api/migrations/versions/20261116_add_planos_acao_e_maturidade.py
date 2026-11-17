"""add_planos_acao_e_maturidade

Revision ID: 20261116_planos_acao_maturidade
Revises: 20261102_rls_policies_hardening
Create Date: 2026-11-16 22:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20261116_planos_acao_maturidade"
down_revision = "20261102_rls_policies_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planos_acao_gerenciais",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("unidade_produtiva_id", sa.Uuid(), nullable=True),
        sa.Column("safra_id", sa.Uuid(), nullable=True),
        sa.Column("tarefa_id", sa.Uuid(), nullable=True),
        sa.Column("responsavel_id", sa.Uuid(), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("origem_indicador", sa.String(length=100), nullable=True),
        sa.Column("responsavel_nome", sa.String(length=150), nullable=True),
        sa.Column("meta", sa.String(length=255), nullable=True),
        sa.Column("prazo", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resultado_obtido", sa.Text(), nullable=True),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["unidades_produtivas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["safra_id"], ["safras.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tarefa_id"], ["campo_tarefas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["responsavel_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_planos_acao_gerenciais_tenant_id", "planos_acao_gerenciais", ["tenant_id"])
    op.create_index("ix_planos_acao_gerenciais_status", "planos_acao_gerenciais", ["status"])

    op.create_table(
        "maturidade_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("unidade_produtiva_id", sa.Uuid(), nullable=True),
        sa.Column("competencia", sa.String(length=7), nullable=False),
        sa.Column("score_geral", sa.Float(), nullable=False),
        sa.Column("pilar_operacional", sa.Float(), nullable=False),
        sa.Column("pilar_agronomico_zootecnico", sa.Float(), nullable=False),
        sa.Column("pilar_economico", sa.Float(), nullable=False),
        sa.Column("pilar_financeiro", sa.Float(), nullable=False),
        sa.Column("detalhes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["unidades_produtivas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "unidade_produtiva_id", "competencia", name="uq_maturidade_competencia"),
    )
    op.create_index("ix_maturidade_snapshots_tenant_id", "maturidade_snapshots", ["tenant_id"])
    op.create_index("ix_maturidade_snapshots_competencia", "maturidade_snapshots", ["competencia"])


def downgrade() -> None:
    op.drop_index("ix_maturidade_snapshots_competencia", table_name="maturidade_snapshots")
    op.drop_index("ix_maturidade_snapshots_tenant_id", table_name="maturidade_snapshots")
    op.drop_table("maturidade_snapshots")
    op.drop_index("ix_planos_acao_gerenciais_status", table_name="planos_acao_gerenciais")
    op.drop_index("ix_planos_acao_gerenciais_tenant_id", table_name="planos_acao_gerenciais")
    op.drop_table("planos_acao_gerenciais")
