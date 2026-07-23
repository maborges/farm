"""vincula compras_pedidos ao cadastro real de Fornecedor + condicoes_pagamento

Revision ID: 20260722b_pedido_fornecedor
Revises: 20260722_estoque_fornecedor
Create Date: 2026-07-22

Idempotente/resumível: usa IF NOT EXISTS / checagens de catálogo, já que uma
execução anterior pode ter avançado parcialmente (colunas criadas, backfill
incompleto) antes de falhar.
"""
from alembic import op

revision = "20260722b_pedido_fornecedor"
down_revision = "20260722_estoque_fornecedor"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE compras_pedidos ADD COLUMN IF NOT EXISTS fornecedor_id UUID")
    op.execute("ALTER TABLE compras_pedidos ADD COLUMN IF NOT EXISTS condicoes_pagamento VARCHAR(100)")

    # Backfill: casa fornecedor_nome do pedido com Fornecedor existente do tenant.
    op.execute("""
        UPDATE compras_pedidos p
        SET fornecedor_id = f.id
        FROM compras_fornecedores f
        WHERE p.fornecedor_id IS NULL
          AND f.tenant_id = p.tenant_id
          AND f.nome_fantasia = p.fornecedor_nome
    """)

    # Para pedidos sem fornecedor cadastrado correspondente, cria o cadastro
    # a partir do texto legado (fornecedor_nome/fornecedor_contato) e vincula.
    # fornecedor_contato é texto livre (pode ser e-mail ou telefone) — telefone
    # tem limite de 20 chars, então só vai para lá se couber; senão vira email
    # (se parecer e-mail) ou fica em branco.
    op.execute("""
        INSERT INTO compras_fornecedores (id, tenant_id, nome_fantasia, telefone, email)
        SELECT DISTINCT ON (p.tenant_id, p.fornecedor_nome)
            gen_random_uuid(),
            p.tenant_id,
            p.fornecedor_nome,
            CASE WHEN p.fornecedor_contato IS NOT NULL
                      AND length(p.fornecedor_contato) <= 20
                      AND p.fornecedor_contato NOT LIKE '%@%'
                 THEN p.fornecedor_contato END,
            CASE WHEN p.fornecedor_contato LIKE '%@%'
                      AND length(p.fornecedor_contato) <= 100
                 THEN p.fornecedor_contato END
        FROM compras_pedidos p
        WHERE p.fornecedor_id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM compras_fornecedores f
              WHERE f.tenant_id = p.tenant_id AND f.nome_fantasia = p.fornecedor_nome
          )
    """)

    op.execute("""
        UPDATE compras_pedidos p
        SET fornecedor_id = f.id
        FROM compras_fornecedores f
        WHERE p.fornecedor_id IS NULL
          AND f.tenant_id = p.tenant_id
          AND f.nome_fantasia = p.fornecedor_nome
    """)

    op.execute("""
        UPDATE compras_pedidos p
        SET condicoes_pagamento = f.condicoes_pagamento
        FROM compras_fornecedores f
        WHERE p.fornecedor_id = f.id
          AND p.condicoes_pagamento IS NULL
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_compras_pedidos_fornecedor_id'
            ) THEN
                ALTER TABLE compras_pedidos
                    ADD CONSTRAINT fk_compras_pedidos_fornecedor_id
                    FOREIGN KEY (fornecedor_id) REFERENCES compras_fornecedores (id);
            END IF;
        END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_compras_pedidos_fornecedor_id ON compras_pedidos (fornecedor_id)")
    op.execute("COMMIT")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_compras_pedidos_fornecedor_id")
    op.execute("ALTER TABLE compras_pedidos DROP CONSTRAINT IF EXISTS fk_compras_pedidos_fornecedor_id")
    op.execute("ALTER TABLE compras_pedidos DROP COLUMN IF EXISTS condicoes_pagamento")
    op.execute("ALTER TABLE compras_pedidos DROP COLUMN IF EXISTS fornecedor_id")
    op.execute("COMMIT")
