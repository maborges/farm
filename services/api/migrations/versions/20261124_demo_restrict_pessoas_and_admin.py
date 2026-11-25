"""Remove acesso a /cadastros/pessoas do perfil global Demonstração.

Revision ID: 20261124_demo_restrict_pessoas
Revises: 20261123_demo_readonly_profile
Create Date: 2026-11-24 09:05:00.000000
"""

from __future__ import annotations

import json
import sqlalchemy as sa
from alembic import op

from core.constants import DEMO_READ_ONLY_PERMISSIONS

revision: str = "20261124_demo_restrict_pessoas"
down_revision: str | None = "20261123_demo_readonly_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Sincroniza permissões do perfil Demonstração removendo cadastros:pessoas:*."""
    conn = op.get_bind()
    perms_json = json.dumps({"granted": DEMO_READ_ONLY_PERMISSIONS})
    conn.execute(
        sa.text(
            """
            UPDATE perfis_acesso
            SET permissoes = CAST(:perms AS json)
            WHERE is_demo_profile = true
               OR (tenant_id IS NULL AND lower(trim(nome)) IN ('demonstração', 'demonstracao'))
            """
        ),
        {"perms": perms_json},
    )


def downgrade() -> None:
    """Sem alteração de schema; apenas ajuste declarativo de permissões."""
    pass
