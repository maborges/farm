"""Adiciona acao/acao_em em notificacoes_leituras — notificações acionáveis

Suporta o modelo de "notificação acionável": botões (Aceitar/Pagar/Adiar/
Descartar) declarados em Notificacao.meta.acoes, com o disparo registrado
por usuário em notificacoes_leituras (mesma linha do estado de leitura).

Revision ID: 20260814_notif_leituras_acao
Revises: 20260814_notificacoes_leituras
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa

revision = "20260814_notif_leituras_acao"
down_revision = "20260814_notificacoes_leituras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notificacoes_leituras", sa.Column("acao", sa.String(30), nullable=True))
    op.add_column("notificacoes_leituras", sa.Column("acao_em", sa.DateTime(timezone=True), nullable=True))
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_column("notificacoes_leituras", "acao_em")
    op.drop_column("notificacoes_leituras", "acao")
    op.execute("COMMIT")
