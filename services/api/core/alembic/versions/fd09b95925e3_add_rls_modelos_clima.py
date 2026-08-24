"""add_rls_modelos_clima

Revision ID: fd09b95925e3
Revises: fc09b95925e2
Create Date: 2026-08-23 20:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd09b95925e3'
down_revision = 'fc09b95925e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ativa RLS nas tabelas
    op.execute("ALTER TABLE modelos_zoosanitarios ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE modelos_fitossanitarios ENABLE ROW LEVEL SECURITY;")

    # Criação das políticas para modelos_zoosanitarios
    # SELECT: Dono do tenant ou registros globais (NULL)
    op.execute("""
        CREATE POLICY select_modelos_zoosanitarios ON modelos_zoosanitarios
        FOR SELECT
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid OR tenant_id IS NULL);
    """)
    # INSERT, UPDATE, DELETE: Somente para o dono (impede alterar globais ou de terceiros através da API de tenant)
    op.execute("""
        CREATE POLICY insert_modelos_zoosanitarios ON modelos_zoosanitarios
        FOR INSERT
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
    """)
    op.execute("""
        CREATE POLICY update_modelos_zoosanitarios ON modelos_zoosanitarios
        FOR UPDATE
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
    """)
    op.execute("""
        CREATE POLICY delete_modelos_zoosanitarios ON modelos_zoosanitarios
        FOR DELETE
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
    """)

    # Criação das políticas para modelos_fitossanitarios
    op.execute("""
        CREATE POLICY select_modelos_fitossanitarios ON modelos_fitossanitarios
        FOR SELECT
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid OR tenant_id IS NULL);
    """)
    op.execute("""
        CREATE POLICY insert_modelos_fitossanitarios ON modelos_fitossanitarios
        FOR INSERT
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
    """)
    op.execute("""
        CREATE POLICY update_modelos_fitossanitarios ON modelos_fitossanitarios
        FOR UPDATE
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
    """)
    op.execute("""
        CREATE POLICY delete_modelos_fitossanitarios ON modelos_fitossanitarios
        FOR DELETE
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY delete_modelos_fitossanitarios ON modelos_fitossanitarios;")
    op.execute("DROP POLICY update_modelos_fitossanitarios ON modelos_fitossanitarios;")
    op.execute("DROP POLICY insert_modelos_fitossanitarios ON modelos_fitossanitarios;")
    op.execute("DROP POLICY select_modelos_fitossanitarios ON modelos_fitossanitarios;")
    op.execute("ALTER TABLE modelos_fitossanitarios DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY delete_modelos_zoosanitarios ON modelos_zoosanitarios;")
    op.execute("DROP POLICY update_modelos_zoosanitarios ON modelos_zoosanitarios;")
    op.execute("DROP POLICY insert_modelos_zoosanitarios ON modelos_zoosanitarios;")
    op.execute("DROP POLICY select_modelos_zoosanitarios ON modelos_zoosanitarios;")
    op.execute("ALTER TABLE modelos_zoosanitarios DISABLE ROW LEVEL SECURITY;")
