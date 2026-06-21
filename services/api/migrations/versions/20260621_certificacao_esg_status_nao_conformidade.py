"""normaliza status de nao conformidade para enum nativo

Revision ID: 20260621_certificacao_esg_status_nao_conformidade
Revises: 20260621_certificacao_esg_lote2
Create Date: 2026-06-21 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


revision = "20260621_certificacao_esg_status_nao_conformidade"
down_revision = "20260621_certificacao_esg_lote2"
branch_labels = None
depends_on = None


status_nao_conformidade_enum = PGEnum(
    "ABERTA",
    "EM_ANALISE",
    "EM_CORRECAO",
    "RESOLVIDA",
    "CANCELADA",
    name="status_nao_conformidade_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    status_nao_conformidade_enum.create(bind, checkfirst=True)
    op.alter_column(
        "certificacao_nao_conformidades",
        "status",
        existing_type=sa.String(length=40),
        type_=status_nao_conformidade_enum,
        postgresql_using="status::status_nao_conformidade_enum",
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.alter_column(
        "certificacao_nao_conformidades",
        "status",
        existing_type=status_nao_conformidade_enum,
        type_=sa.String(length=40),
        postgresql_using="status::text",
        existing_nullable=False,
    )
    status_nao_conformidade_enum.drop(bind, checkfirst=True)
