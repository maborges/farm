"""Adiciona suporte a perfil Demonstração somente consulta, validade e limite simultâneo.

Revision ID: 20261123_demo_readonly_profile
Revises: 20261122_agro_collector_foundation
Create Date: 2026-11-23 18:20:00.000000
"""

from __future__ import annotations

import json
import uuid
import sqlalchemy as sa
from alembic import op

from core.constants import (
    DEMO_CRM_STAGE_NAME,
    DEMO_DEFAULT_DURATION_DAYS,
    DEMO_DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEMO_IDLE_TIMEOUT_MINUTES,
    DEMO_PROFILE_NAME,
    DEMO_READ_ONLY_PERMISSIONS,
)

revision: str = "20261123_demo_readonly_profile"
down_revision: str | None = "20261122_agro_collector_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adiciona colunas de controle de demonstração e realiza seed idempotente."""
    op.add_column(
        "tenants",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "tenants",
        sa.Column("demo_max_sessoes_simultaneas", sa.Integer(), nullable=True),
    )

    op.add_column(
        "perfis_acesso",
        sa.Column("is_read_only", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "perfis_acesso",
        sa.Column("is_demo_profile", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.add_column(
        "tenant_usuarios",
        sa.Column("demo_prorrogacoes_count", sa.Integer(), nullable=False, server_default="0"),
    )

    conn = op.get_bind()

    # Marcar tenant canônico de demonstração se já existir na base
    conn.execute(
        sa.text(
            """
            UPDATE tenants
            SET is_demo = true,
                demo_max_sessoes_simultaneas = COALESCE(demo_max_sessoes_simultaneas, :max_sess)
            WHERE lower(trim(nome)) = 'produtor deepfarms'
            """
        ),
        {"max_sess": DEMO_DEFAULT_MAX_CONCURRENT_SESSIONS},
    )

    # Seed idempotente do perfil global Demonstração
    existing_profile = conn.execute(
        sa.text(
            """
            SELECT id FROM perfis_acesso
            WHERE tenant_id IS NULL
              AND lower(trim(nome)) IN ('demonstração', 'demonstracao')
            LIMIT 1
            """
        )
    ).fetchone()

    perms_json = json.dumps({"granted": DEMO_READ_ONLY_PERMISSIONS})
    if existing_profile:
        conn.execute(
            sa.text(
                """
                UPDATE perfis_acesso
                SET is_read_only = true,
                    is_demo_profile = true,
                    permissoes = CAST(:perms AS json)
                WHERE id = :pid
                """
            ),
            {"pid": existing_profile[0], "perms": perms_json},
        )
    else:
        conn.execute(
            sa.text(
                """
                INSERT INTO perfis_acesso
                    (id, tenant_id, nome, descricao, is_custom, is_read_only, is_demo_profile, permissoes, created_at)
                VALUES
                    (:id, NULL, :nome, :descricao, false, true, true, CAST(:perms AS json), NOW())
                """
            ),
            {
                "id": uuid.uuid4(),
                "nome": DEMO_PROFILE_NAME,
                "descricao": "Visitante de demonstração (somente consulta, sem gravação ou alteração)",
                "perms": perms_json,
            },
        )

    # Seed idempotente do estágio CRM 'Demonstração'
    existing_stage = conn.execute(
        sa.text(
            """
            SELECT id FROM crm_pipeline_estagios
            WHERE lower(trim(nome)) IN ('demonstração', 'demonstracao')
            LIMIT 1
            """
        )
    ).fetchone()

    if not existing_stage:
        next_ordem = conn.execute(
            sa.text("SELECT COALESCE(MAX(ordem), -1) + 1 FROM crm_pipeline_estagios")
        ).scalar_one()
        conn.execute(
            sa.text(
                """
                INSERT INTO crm_pipeline_estagios (id, nome, cor, ordem, ativo, created_at)
                VALUES (:id, :nome, '#0ea5e9', :ordem, true, NOW())
                """
            ),
            {
                "id": uuid.uuid4(),
                "nome": DEMO_CRM_STAGE_NAME,
                "ordem": int(next_ordem),
            },
        )

    # Seed idempotente da chave global 'demonstracao' em configuracoes_saas
    existing_demo_cfg = conn.execute(
        sa.text("SELECT id FROM configuracoes_saas WHERE chave = 'demonstracao' LIMIT 1")
    ).fetchone()
    if not existing_demo_cfg:
        demo_tenant_row = conn.execute(
            sa.text("SELECT id FROM tenants WHERE is_demo = true LIMIT 1")
        ).fetchone()
        demo_cfg_json = json.dumps({
            "tenant_id": str(demo_tenant_row[0]) if demo_tenant_row else None,
            "max_sessoes_simultaneas": DEMO_DEFAULT_MAX_CONCURRENT_SESSIONS,
            "duracao_inicial_dias": DEMO_DEFAULT_DURATION_DAYS,
            "dias_prorrogacao_padrao": DEMO_DEFAULT_DURATION_DAYS,
            "timeout_inatividade_minutos": DEMO_IDLE_TIMEOUT_MINUTES,
            "estagio_crm_nome": DEMO_CRM_STAGE_NAME,
            "mensagem_limite_simultaneo": (
                "Muitos usuários de demonstração estão usando a plataforma no momento. "
                "Por favor, aguarde alguns minutos e tente novamente mais tarde."
            ),
            "permitir_solicitacao_prorrogacao": True,
        })
        conn.execute(
            sa.text(
                """
                INSERT INTO configuracoes_saas (id, chave, valor, descricao, ativo)
                VALUES (:id, 'demonstracao', CAST(:valor AS json), :descricao, true)
                """
            ),
            {
                "id": uuid.uuid4(),
                "valor": demo_cfg_json,
                "descricao": "Parâmetros globais do ambiente de demonstração",
            },
        )


def downgrade() -> None:
    """Remove colunas adicionadas para controle do modo Demonstração."""
    op.drop_column("tenant_usuarios", "demo_prorrogacoes_count")
    op.drop_column("perfis_acesso", "is_demo_profile")
    op.drop_column("perfis_acesso", "is_read_only")
    op.drop_column("tenants", "demo_max_sessoes_simultaneas")
    op.drop_column("tenants", "is_demo")
