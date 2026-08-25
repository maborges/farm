"""Habilita o escopo de configuração climática por unidade produtiva."""

from alembic import op
import sqlalchemy as sa


revision = "20260818_clima_escopo_unidade"
down_revision = "20260816_imoveis_irrigacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_tenant_integracoes_scope_type", "tenant_integracoes", type_="check")
    op.create_check_constraint(
        "ck_tenant_integracoes_scope_type",
        "tenant_integracoes",
        "scope_type IN ('PLATFORM', 'TENANT', 'UNIDADE_PRODUTIVA', 'ESTABELECIMENTO', 'USUARIO')",
    )
    op.execute(
        sa.text(
            """
            INSERT INTO tenant_integracoes (
                tenant_id, integracao_id, status, configuracoes, credenciais,
                webhook_url, webhook_secret, ultima_sincronizacao,
                total_sincronizacoes, installed_at, updated_at, scope_type,
                scope_id, lifecycle_state, connection_payload, credential_ref_id,
                deleted_at
            )
            SELECT
                config.tenant_id, config.integracao_id, config.status,
                config.configuracoes, config.credenciais, config.webhook_url,
                config.webhook_secret, config.ultima_sincronizacao,
                config.total_sincronizacoes, config.installed_at, config.updated_at,
                'UNIDADE_PRODUTIVA', unidades.id::text, config.lifecycle_state,
                config.connection_payload, config.credential_ref_id, config.deleted_at
            FROM tenant_integracoes config
            JOIN marketplace_integracoes provider
              ON provider.id = config.integracao_id
             AND provider.slug = 'openweather'
            JOIN unidades_produtivas unidades
              ON unidades.tenant_id = config.tenant_id
             AND unidades.ativo IS TRUE
            WHERE config.scope_type = 'TENANT'
              AND config.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM tenant_integracoes existing
                  WHERE existing.tenant_id = config.tenant_id
                    AND existing.integracao_id = config.integracao_id
                    AND existing.scope_type = 'UNIDADE_PRODUTIVA'
                    AND existing.scope_id = unidades.id::text
                    AND existing.deleted_at IS NULL
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                uq_tenant_integracoes_provider_scope_active
            ON tenant_integracoes (tenant_id, integracao_id, scope_type, scope_id)
            WHERE deleted_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_tenant_integracoes_provider_scope_active"))
    op.drop_constraint("ck_tenant_integracoes_scope_type", "tenant_integracoes", type_="check")
    op.create_check_constraint(
        "ck_tenant_integracoes_scope_type",
        "tenant_integracoes",
        "scope_type IN ('PLATFORM', 'TENANT', 'ESTABELECIMENTO', 'USUARIO')",
    )
