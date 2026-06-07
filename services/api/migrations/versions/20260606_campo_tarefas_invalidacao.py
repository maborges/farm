"""campo_tarefas invalidacao audit fields

Revision ID: 20260606_campo_tarefas_invalidacao
Revises: 20260508_campo_pwa_05
Create Date: 2026-06-06 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260606_campo_tarefas_invalidacao"
down_revision: Union[str, Sequence[str], None] = "20260508_campo_pwa_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("campo_tarefas")}

    if "invalidado_em" not in columns:
        op.add_column("campo_tarefas", sa.Column("invalidado_em", sa.DateTime(), nullable=True))
    if "invalidado_por" not in columns:
        op.add_column("campo_tarefas", sa.Column("invalidado_por", sa.Uuid(), nullable=True))
    if "motivo_invalidacao" not in columns:
        op.add_column("campo_tarefas", sa.Column("motivo_invalidacao", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campo_tarefas", "motivo_invalidacao")
    op.drop_column("campo_tarefas", "invalidado_por")
    op.drop_column("campo_tarefas", "invalidado_em")
