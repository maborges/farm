"""Fortalece snapshot e assinatura documental do caderno.

Revision ID: 20260606_field_remediation_01_snapshot
Revises: 20260606_field_remediation_01_merge
Create Date: 2026-06-06 00:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260606_field_remediation_01_snapshot"
down_revision: Union[str, Sequence[str], None] = "20260606_field_remediation_01_merge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_column(bind, table_name: str, column: sa.Column) -> None:
    columns = {item["name"] for item in inspect(bind).get_columns(table_name)}
    if column.name in columns:
        return
    op.add_column(table_name, column)


def _ensure_index(bind, table_name: str, index_name: str, columns: list[str]) -> None:
    indexes = {item["name"] for item in inspect(bind).get_indexes(table_name)}
    if index_name in indexes:
        return
    op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    bind = op.get_bind()

    _ensure_column(bind, "caderno_exportacoes", sa.Column("snapshot_documental", sa.JSON(), nullable=True))
    _ensure_column(bind, "caderno_exportacoes", sa.Column("snapshot_hash", sa.String(length=128), nullable=True))
    _ensure_column(bind, "caderno_exportacoes", sa.Column("protocolo_documental", sa.String(length=64), nullable=True))
    _ensure_column(bind, "caderno_exportacoes", sa.Column("usuario_assinatura_id", sa.Uuid(), nullable=True))
    _ensure_index(bind, "caderno_exportacoes", "ix_caderno_exportacoes_protocolo_documental", ["protocolo_documental"])


def downgrade() -> None:
    op.drop_index("ix_caderno_exportacoes_protocolo_documental", table_name="caderno_exportacoes")
    op.drop_column("caderno_exportacoes", "usuario_assinatura_id")
    op.drop_column("caderno_exportacoes", "protocolo_documental")
    op.drop_column("caderno_exportacoes", "snapshot_hash")
    op.drop_column("caderno_exportacoes", "snapshot_documental")
