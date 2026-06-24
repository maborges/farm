"""allow pecuaria vacinacao origin in estoque_movimentos

Revision ID: 20260624_pecuaria_vacinacao_origem_estoque
Revises: b808f67e400b
Create Date: 2026-06-24
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_pecuaria_vacinacao_origem_estoque"
down_revision: Union[str, Sequence[str], None] = "b808f67e400b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ALLOWED_ORIGINS = (
    "OPERACAO_EXECUCAO",
    "COMPRA",
    "COLHEITA",
    "AJUSTE",
    "MANUAL",
    "TRANSFERENCIA",
    "LEGADO",
    "IMPLANTACAO",
    "PECUARIA_VACINACAO",
)
ALLOWED_ORIGINS_SQL = ",".join(f"'{origin}'" for origin in ALLOWED_ORIGINS)


def _recreate_check() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("estoque_movimentos")}
    if "ck_estoque_movimentos_origem" in constraints:
        op.drop_constraint("ck_estoque_movimentos_origem", "estoque_movimentos", type_="check")
    op.create_check_constraint(
        "ck_estoque_movimentos_origem",
        "estoque_movimentos",
        f"origem IN ({ALLOWED_ORIGINS_SQL})",
    )


def upgrade() -> None:
    _recreate_check()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("estoque_movimentos")}
    if "ck_estoque_movimentos_origem" in constraints:
        op.drop_constraint("ck_estoque_movimentos_origem", "estoque_movimentos", type_="check")
    op.create_check_constraint(
        "ck_estoque_movimentos_origem",
        "estoque_movimentos",
        "origem IN ('OPERACAO_EXECUCAO','COMPRA','COLHEITA','AJUSTE','MANUAL','TRANSFERENCIA','LEGADO','IMPLANTACAO')",
    )
