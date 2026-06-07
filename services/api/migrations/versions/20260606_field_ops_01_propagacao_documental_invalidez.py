"""field_ops_01_propagacao_documental_invalidez

Revision ID: 20260606_field_ops_01
Revises: step45_tarefas_invalidacao
Create Date: 2026-06-06 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260606_field_ops_01"
down_revision: Union[str, Sequence[str], None] = "step45_tarefas_invalidacao"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_column(bind, table_name: str, column_name: str, column_type, *, default_sql: str | None = None) -> None:
    columns = {column["name"] for column in inspect(bind).get_columns(table_name)}
    if column_name in columns:
        return
    if default_sql is not None:
        op.add_column(
            table_name,
            sa.Column(column_name, column_type, nullable=False, server_default=sa.text(default_sql)),
        )
    else:
        op.add_column(table_name, sa.Column(column_name, column_type, nullable=True))


def upgrade() -> None:
    bind = op.get_bind()
    indexes_caderno = {item["name"] for item in inspect(bind).get_indexes("caderno_campo_entradas")}
    indexes_operacoes = {item["name"] for item in inspect(bind).get_indexes("operacoes_agricolas")}

    _ensure_column(bind, "caderno_campo_entradas", "origem_invalidada", sa.Boolean(), default_sql="FALSE")
    _ensure_column(bind, "caderno_campo_entradas", "origem_invalidada_em", sa.DateTime())
    _ensure_column(bind, "caderno_campo_entradas", "origem_invalidada_por", sa.Uuid())
    _ensure_column(bind, "caderno_campo_entradas", "motivo_invalidacao_origem", sa.Text())
    if "ix_caderno_campo_origem_invalidada" not in indexes_caderno:
        op.create_index(
            "ix_caderno_campo_origem_invalidada",
            "caderno_campo_entradas",
            ["tenant_id", "origem_invalidada"],
            unique=False,
        )

    _ensure_column(bind, "operacoes_agricolas", "origem_invalidada", sa.Boolean(), default_sql="FALSE")
    _ensure_column(bind, "operacoes_agricolas", "origem_invalidada_em", sa.DateTime())
    _ensure_column(bind, "operacoes_agricolas", "origem_invalidada_por", sa.Uuid())
    _ensure_column(bind, "operacoes_agricolas", "motivo_invalidacao_origem", sa.Text())
    if "ix_operacoes_origem_invalidada" not in indexes_operacoes:
        op.create_index(
            "ix_operacoes_origem_invalidada",
            "operacoes_agricolas",
            ["tenant_id", "origem_invalidada"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_operacoes_origem_invalidada", table_name="operacoes_agricolas")
    op.drop_column("operacoes_agricolas", "motivo_invalidacao_origem")
    op.drop_column("operacoes_agricolas", "origem_invalidada_por")
    op.drop_column("operacoes_agricolas", "origem_invalidada_em")
    op.drop_column("operacoes_agricolas", "origem_invalidada")

    op.drop_index("ix_caderno_campo_origem_invalidada", table_name="caderno_campo_entradas")
    op.drop_column("caderno_campo_entradas", "motivo_invalidacao_origem")
    op.drop_column("caderno_campo_entradas", "origem_invalidada_por")
    op.drop_column("caderno_campo_entradas", "origem_invalidada_em")
    op.drop_column("caderno_campo_entradas", "origem_invalidada")
