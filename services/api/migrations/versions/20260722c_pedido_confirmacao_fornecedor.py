"""cria tabela de confirmacao de pedido pelo fornecedor (link + senha por e-mail)

Revision ID: 20260722c_pedido_confirmacao
Revises: 20260722b_pedido_fornecedor
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260722c_pedido_confirmacao"
down_revision = "20260722b_pedido_fornecedor"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS compras_pedidos_confirmacoes (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            pedido_id UUID NOT NULL REFERENCES compras_pedidos(id) ON DELETE CASCADE,
            token_confirmacao VARCHAR(100) NOT NULL,
            senha_confirmacao_hash VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            tentativas_senha INTEGER NOT NULL DEFAULT 0,
            data_expiracao TIMESTAMPTZ NOT NULL,
            respondido_em TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_compras_pedidos_confirmacoes_tenant_id ON compras_pedidos_confirmacoes (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_compras_pedidos_confirmacoes_pedido_id ON compras_pedidos_confirmacoes (pedido_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_compras_pedidos_confirmacoes_token_confirmacao ON compras_pedidos_confirmacoes (token_confirmacao)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_compras_pedidos_confirmacoes_status ON compras_pedidos_confirmacoes (status)")
    op.execute("COMMIT")


def downgrade():
    op.execute("DROP TABLE IF EXISTS compras_pedidos_confirmacoes")
    op.execute("COMMIT")
