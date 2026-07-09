"""Add legacy gateway login fields to sankhya_config.

Revision ID: 20260709_sankhya_legacy_gateway_login
Revises: 20260706_integrations_external_record_links_pending_local
Create Date: 2026-07-09 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260709_sankhya_legacy_gateway_login"
down_revision = "20260706_integrations_external_record_links_pending_local"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sankhya_config") as batch_op:
        batch_op.add_column(sa.Column("token", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("appkey", sa.String(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sankhya_config") as batch_op:
        batch_op.drop_column("appkey")
        batch_op.drop_column("token")
