"""allow pending external links without local record id

Revision ID: 20260706_integrations_external_record_links_pending_local
Revises: 20260706_integrations_external_record_links
Create Date: 2026-07-06 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260706_integrations_external_record_links_pending_local"
down_revision = "20260706_integrations_external_record_links"
branch_labels = None
depends_on = None


SCHEMA = "farms"
LINK_TABLE = "integration_external_record_links"


def upgrade() -> None:
    op.alter_column(
        LINK_TABLE,
        "local_record_id",
        existing_type=sa.String(length=100),
        nullable=True,
        schema=SCHEMA,
        comment="Identificador do registro local. Pode ficar nulo enquanto a associacao estiver pendente.",
    )


def downgrade() -> None:
    op.alter_column(
        LINK_TABLE,
        "local_record_id",
        existing_type=sa.String(length=100),
        nullable=False,
        schema=SCHEMA,
        comment="Identificador do registro local.",
    )
