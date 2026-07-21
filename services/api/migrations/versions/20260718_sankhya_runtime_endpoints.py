"""Publicar endpoints homologados das features Sankhya existentes.

Revision ID: 20260718_sankhya_endpoints
Revises: 20260718_sankhya_tenant_keys
Create Date: 2026-07-18
"""

import json

from alembic import op
from sqlalchemy import text

revision = "20260718_sankhya_endpoints"
down_revision = "20260718_sankhya_tenant_keys"
branch_labels = None
depends_on = None

ENDPOINTS = {
    "pessoas": {
        "module": "mge",
        "service_name": "CRUDServiceProvider.loadRecords",
        "entity": "Parceiro",
        "path": "/gateway/v1/mge/service.sbr",
        "query": {
            "serviceName": "CRUDServiceProvider.loadRecords",
            "outputType": "json",
        },
    },
    "produtos": {
        "module": "mge",
        "service_name": "CRUDServiceProvider.loadRecords",
        "entity": "Produto",
        "path": "/gateway/v1/mge/service.sbr",
        "query": {
            "serviceName": "CRUDServiceProvider.loadRecords",
            "outputType": "json",
        },
    },
}


def upgrade() -> None:
    """Adicionar metadados derivados sem alterar configuração ou credenciais."""
    connection = op.get_bind()
    for feature_code, endpoint in ENDPOINTS.items():
        connection.execute(
            text(
                """
                UPDATE farms.integration_features AS feature
                   SET settings_payload = jsonb_set(
                       COALESCE(feature.settings_payload::jsonb, '{}'::jsonb),
                       '{runtime_endpoint}',
                       CAST(:endpoint AS jsonb),
                       true
                   )
                  FROM farms.tenant_integracoes AS config
                  JOIN farms.marketplace_integracoes AS provider
                    ON provider.id = config.integracao_id
                 WHERE feature.config_id = config.id
                   AND provider.slug = 'sankhya'
                   AND feature.codigo = :feature_code
                   AND feature.deleted_at IS NULL
                   AND config.deleted_at IS NULL
                """
            ),
            {"endpoint": json.dumps(endpoint), "feature_code": feature_code},
        )


def downgrade() -> None:
    """Remover somente os metadados derivados desta revisão."""
    op.execute(
        """
        UPDATE farms.integration_features AS feature
           SET settings_payload = feature.settings_payload::jsonb - 'runtime_endpoint'
          FROM farms.tenant_integracoes AS config
          JOIN farms.marketplace_integracoes AS provider
            ON provider.id = config.integracao_id
         WHERE feature.config_id = config.id
           AND provider.slug = 'sankhya'
           AND feature.codigo IN ('pessoas', 'produtos')
        """
    )
