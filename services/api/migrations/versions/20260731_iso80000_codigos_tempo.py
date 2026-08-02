"""Ajusta códigos das unidades de tempo para os símbolos oficiais da ISO 80000-3

Revision ID: 20260731_uom_iso80000
Revises: 20260731_uom_periodo
Create Date: 2026-07-31

Dado puro (sem mudança de schema). ISO 80000-3 define símbolo oficial para:
  SEGUNDO -> s
  MINUTO  -> min
  HORA    -> h
  DIA     -> d
  ANO     -> a (annum)

SEMANA, MES, MANHA, TARDE, NOITE não têm símbolo definido na norma (não são
unidades SI/ISO) — mantidos como estavam, por decisão do usuário.

Como HORA é a unidade-base da dimensão 'tempo', seu novo código ('h') precisa
se propagar para codigo_referencia de todas as unidades da dimensão.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260731_uom_iso80000"
down_revision: Union[str, Sequence[str], None] = "20260731_uom_periodo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A linha HORA (eh_unidade_base=true) exige codigo == codigo_referencia
    # no mesmo instante (constraint de coerência) — atualiza as duas juntas.
    op.execute(
        "UPDATE unidades_medida SET codigo = 'h', codigo_referencia = 'h' "
        "WHERE codigo = 'HORA' AND dimensao = 'tempo'"
    )
    # Demais unidades da dimensão (não são a base) — só o ponteiro de referência muda.
    op.execute(
        "UPDATE unidades_medida SET codigo_referencia = 'h' "
        "WHERE dimensao = 'tempo' AND codigo <> 'h'"
    )
    op.execute("UPDATE unidades_medida SET codigo = 's' WHERE codigo = 'SEGUNDO' AND dimensao = 'tempo'")
    op.execute("UPDATE unidades_medida SET codigo = 'min' WHERE codigo = 'MINUTO' AND dimensao = 'tempo'")
    op.execute("UPDATE unidades_medida SET codigo = 'd' WHERE codigo = 'DIA' AND dimensao = 'tempo'")
    op.execute("UPDATE unidades_medida SET codigo = 'a' WHERE codigo = 'ANO' AND dimensao = 'tempo'")


def downgrade() -> None:
    op.execute("UPDATE unidades_medida SET codigo = 'ANO' WHERE codigo = 'a' AND dimensao = 'tempo'")
    op.execute("UPDATE unidades_medida SET codigo = 'DIA' WHERE codigo = 'd' AND dimensao = 'tempo'")
    op.execute("UPDATE unidades_medida SET codigo = 'MINUTO' WHERE codigo = 'min' AND dimensao = 'tempo'")
    op.execute("UPDATE unidades_medida SET codigo = 'SEGUNDO' WHERE codigo = 's' AND dimensao = 'tempo'")
    op.execute(
        "UPDATE unidades_medida SET codigo_referencia = 'HORA' "
        "WHERE dimensao = 'tempo' AND codigo <> 'h'"
    )
    op.execute(
        "UPDATE unidades_medida SET codigo = 'HORA', codigo_referencia = 'HORA' "
        "WHERE codigo = 'h' AND dimensao = 'tempo'"
    )
