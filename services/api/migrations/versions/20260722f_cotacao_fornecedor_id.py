"""vincula compras_cotacoes ao cadastro real de Fornecedor + condicoes_pagamento

A negociação da forma de pagamento agora é capturada na própria cotação
(antes só existia o padrão do cadastro do Fornecedor, aplicado tarde demais
na aprovação do pedido).

Revision ID: 20260722f_cotacao_fornecedor
Revises: 20260722e_fornecedor_sem_dup
Create Date: 2026-07-22
"""
from alembic import op

revision = "20260722f_cotacao_fornecedor"
down_revision = "20260722e_fornecedor_sem_dup"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE compras_cotacoes ADD COLUMN IF NOT EXISTS fornecedor_id UUID")
    op.execute("ALTER TABLE compras_cotacoes ADD COLUMN IF NOT EXISTS condicoes_pagamento VARCHAR(100)")

    # Backfill: casa fornecedor_nome da cotação com Fornecedor existente do tenant.
    op.execute("""
        UPDATE compras_cotacoes c
        SET fornecedor_id = f.id
        FROM compras_fornecedores f
        JOIN cadastros_pessoas p ON p.id = f.pessoa_id
        WHERE c.fornecedor_id IS NULL
          AND f.tenant_id = c.tenant_id
          AND p.nome_exibicao = c.fornecedor_nome
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_compras_cotacoes_fornecedor_id'
            ) THEN
                ALTER TABLE compras_cotacoes
                    ADD CONSTRAINT fk_compras_cotacoes_fornecedor_id
                    FOREIGN KEY (fornecedor_id) REFERENCES compras_fornecedores (id);
            END IF;
        END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_compras_cotacoes_fornecedor_id ON compras_cotacoes (fornecedor_id)")
    op.execute("COMMIT")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_compras_cotacoes_fornecedor_id")
    op.execute("ALTER TABLE compras_cotacoes DROP CONSTRAINT IF EXISTS fk_compras_cotacoes_fornecedor_id")
    op.execute("ALTER TABLE compras_cotacoes DROP COLUMN IF EXISTS condicoes_pagamento")
    op.execute("ALTER TABLE compras_cotacoes DROP COLUMN IF EXISTS fornecedor_id")
    op.execute("COMMIT")
