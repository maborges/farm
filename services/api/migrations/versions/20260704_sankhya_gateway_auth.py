"""Sankhya Gateway auth credentials.

Revision ID: 20260704_sankhya_gateway_auth
Revises: 20260703_ops_intelligence_02_recommendations_foundation
Create Date: 2026-07-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260704_sankhya_gateway_auth"
down_revision = "20260703_ops_intelligence_02_recommendations_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sankhya_config") as batch_op:
        batch_op.add_column(sa.Column("environment", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("api_base_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("auth_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("client_id", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("client_secret", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("x_token", sa.String(length=200), nullable=True))
        batch_op.alter_column("ws_url", existing_type=sa.String(length=500), nullable=True)
        batch_op.alter_column("username", existing_type=sa.String(length=100), nullable=True)
        batch_op.alter_column("password", existing_type=sa.String(length=200), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("sankhya_config") as batch_op:
        batch_op.alter_column("password", existing_type=sa.String(length=200), nullable=False)
        batch_op.alter_column("username", existing_type=sa.String(length=100), nullable=False)
        batch_op.alter_column("ws_url", existing_type=sa.String(length=500), nullable=False)
        batch_op.drop_column("x_token")
        batch_op.drop_column("client_secret")
        batch_op.drop_column("client_id")
        batch_op.drop_column("auth_url")
        batch_op.drop_column("api_base_url")
        batch_op.drop_column("environment")
