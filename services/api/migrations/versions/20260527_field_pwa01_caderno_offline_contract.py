"""field_pwa01_caderno_offline_contract

Revision ID: 20260527_field_pwa01
Revises: 20260527_field_core05
Create Date: 2026-05-27 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260527_field_pwa01"
down_revision: Union[str, Sequence[str], None] = "20260527_field_core05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("caderno_campo_entradas")}

    if "device_id" not in columns:
        op.add_column("caderno_campo_entradas", sa.Column("device_id", sa.Uuid(), nullable=True))
    if "unidade_produtiva_id" not in columns:
        op.add_column("caderno_campo_entradas", sa.Column("unidade_produtiva_id", sa.Uuid(), nullable=True))
    if "client_created_at" not in columns:
        op.add_column("caderno_campo_entradas", sa.Column("client_created_at", sa.DateTime(), nullable=True))
    if "client_updated_at" not in columns:
        op.add_column("caderno_campo_entradas", sa.Column("client_updated_at", sa.DateTime(), nullable=True))
    if "payload_operacional" not in columns:
        op.add_column("caderno_campo_entradas", sa.Column("payload_operacional", sa.JSON(), nullable=True))

    indexes = {item["name"] for item in inspector.get_indexes("caderno_campo_entradas")}
    if "ix_caderno_campo_device_id" not in indexes:
        op.create_index("ix_caderno_campo_device_id", "caderno_campo_entradas", ["device_id"])
    if "ix_caderno_campo_unidade_produtiva_id" not in indexes:
        op.create_index("ix_caderno_campo_unidade_produtiva_id", "caderno_campo_entradas", ["unidade_produtiva_id"])
    if "ix_caderno_campo_client_created_at" not in indexes:
        op.create_index("ix_caderno_campo_client_created_at", "caderno_campo_entradas", ["client_created_at"])


def downgrade() -> None:
    op.drop_index("ix_caderno_campo_client_created_at", table_name="caderno_campo_entradas")
    op.drop_index("ix_caderno_campo_unidade_produtiva_id", table_name="caderno_campo_entradas")
    op.drop_index("ix_caderno_campo_device_id", table_name="caderno_campo_entradas")
    op.drop_column("caderno_campo_entradas", "payload_operacional")
    op.drop_column("caderno_campo_entradas", "client_updated_at")
    op.drop_column("caderno_campo_entradas", "client_created_at")
    op.drop_column("caderno_campo_entradas", "unidade_produtiva_id")
    op.drop_column("caderno_campo_entradas", "device_id")
