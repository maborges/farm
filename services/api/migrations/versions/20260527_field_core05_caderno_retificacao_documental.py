"""field_core05_caderno_retificacao_documental

Revision ID: 20260527_field_core05
Revises: 20260527_field_core04
Create Date: 2026-05-27 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260527_field_core05"
down_revision: Union[str, Sequence[str], None] = "20260527_field_core04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("caderno_campo_entradas", sa.Column("retifica_evento_id", sa.Uuid(), nullable=True))
    op.add_column("caderno_campo_entradas", sa.Column("retificado_por_evento_id", sa.Uuid(), nullable=True))
    op.add_column("caderno_campo_entradas", sa.Column("motivo_retificacao", sa.Text(), nullable=True))
    op.add_column("caderno_campo_entradas", sa.Column("retificado_em", sa.DateTime(), nullable=True))
    op.add_column("caderno_campo_entradas", sa.Column("retificado_por_usuario_id", sa.Uuid(), nullable=True))

    op.create_index("ix_caderno_campo_retifica_evento", "caderno_campo_entradas", ["retifica_evento_id"])
    op.create_index("ix_caderno_campo_retificado_por_evento", "caderno_campo_entradas", ["retificado_por_evento_id"])

    op.create_foreign_key(
        "fk_caderno_campo_retifica_evento",
        "caderno_campo_entradas",
        "caderno_campo_entradas",
        ["retifica_evento_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_caderno_campo_retificado_por_evento",
        "caderno_campo_entradas",
        "caderno_campo_entradas",
        ["retificado_por_evento_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_caderno_campo_retificado_por_evento", "caderno_campo_entradas", type_="foreignkey")
    op.drop_constraint("fk_caderno_campo_retifica_evento", "caderno_campo_entradas", type_="foreignkey")
    op.drop_index("ix_caderno_campo_retificado_por_evento", table_name="caderno_campo_entradas")
    op.drop_index("ix_caderno_campo_retifica_evento", table_name="caderno_campo_entradas")
    op.drop_column("caderno_campo_entradas", "retificado_por_usuario_id")
    op.drop_column("caderno_campo_entradas", "retificado_em")
    op.drop_column("caderno_campo_entradas", "motivo_retificacao")
    op.drop_column("caderno_campo_entradas", "retificado_por_evento_id")
    op.drop_column("caderno_campo_entradas", "retifica_evento_id")
