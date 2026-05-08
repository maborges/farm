"""growth_landing_eventos

Revision ID: 20260507_growth_landing
Revises: 20260507_merge_frota_growth
Create Date: 2026-05-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260507_growth_landing"
down_revision: Union[str, Sequence[str], None] = "20260507_merge_frota_growth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "growth_landing_eventos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sessao_id", sa.String(100), nullable=False),
        sa.Column("evento", sa.String(60), nullable=False),
        sa.Column("device", sa.String(20), nullable=True),
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("utm_medium", sa.String(100), nullable=True),
        sa.Column("headline_variant", sa.String(5), nullable=True),
        sa.Column("path", sa.String(200), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_landing_evento_nome", "growth_landing_eventos", ["evento"])
    op.create_index("ix_landing_evento_created_at", "growth_landing_eventos", ["created_at"])
    op.create_index("ix_landing_evento_variant", "growth_landing_eventos", ["headline_variant"])
    op.create_index("ix_landing_evento_sessao", "growth_landing_eventos", ["sessao_id"])


def downgrade() -> None:
    op.drop_index("ix_landing_evento_sessao", "growth_landing_eventos")
    op.drop_index("ix_landing_evento_variant", "growth_landing_eventos")
    op.drop_index("ix_landing_evento_created_at", "growth_landing_eventos")
    op.drop_index("ix_landing_evento_nome", "growth_landing_eventos")
    op.drop_table("growth_landing_eventos")
