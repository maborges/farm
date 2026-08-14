"""Adiciona notificacoes_leituras — estado de leitura por usuário

Antes, Notificacao.lida era um campo único tenant-wide: qualquer usuário
marcando como lida afetava todos os outros do mesmo tenant. Esta tabela
introduz leitura por usuário (ausência de linha = não lida).

Revision ID: 20260814_notificacoes_leituras
Revises: 20260808_sankhya_numeric_monetario
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260814_notificacoes_leituras"
down_revision = "20260808_sankhya_numeric_monetario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notificacoes_leituras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "notificacao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notificacoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lida", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.UniqueConstraint("notificacao_id", "usuario_id", name="uq_notificacao_leitura_usuario"),
    )
    op.create_index(
        "ix_notificacoes_leituras_tenant_usuario",
        "notificacoes_leituras",
        ["tenant_id", "usuario_id"],
    )
    op.create_index(
        op.f("ix_notificacoes_leituras_tenant_id"),
        "notificacoes_leituras",
        ["tenant_id"],
    )
    op.create_index(
        op.f("ix_notificacoes_leituras_notificacao_id"),
        "notificacoes_leituras",
        ["notificacao_id"],
    )
    op.create_index(
        op.f("ix_notificacoes_leituras_usuario_id"),
        "notificacoes_leituras",
        ["usuario_id"],
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_table("notificacoes_leituras")
    op.execute("COMMIT")
