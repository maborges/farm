"""Merge heads para FIELD-REMEDIATION-01.

Revision ID: 20260606_field_remediation_01_merge
Revises: 20260524_frota_step08, 20260527_field_pwa01, 20260606_campo_tarefas_invalidacao, 20260606_field_ops_01
Create Date: 2026-06-06 00:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "20260606_field_remediation_01_merge"
down_revision: Union[str, Sequence[str], None] = (
    "20260524_frota_step08",
    "20260527_field_pwa01",
    "20260606_campo_tarefas_invalidacao",
    "20260606_field_ops_01",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
