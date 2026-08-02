"""Seed de unidades de tempo corrido (DIA, HORA, MINUTO) na dimensão 'tempo'

Revision ID: 20260731_uom_tempo
Revises: 20260731_uom_rename
Create Date: 2026-07-31

Aditivo: apenas insere 3 novas unidades globais (tenant_id=NULL, sistema=true)
na dimensão 'tempo' (já prevista no CHECK constraint da tabela, e livre —
não usada por nenhum registro, já que hora_homem/hora_maquina são dimensões
próprias, tipos de recurso, não tempo corrido).

Unidade-base da dimensão: HORA (fator_referencia=1).
  DIA    -> fator_referencia=24         (1 dia = 24 horas)
  MINUTO -> fator_referencia=0.016666667 (1 minuto = 1/60 hora)

Permite conversão direta (mesma dimensão) via fator_referencia, sem
depender de unidades_medida_conversoes: valor_destino = valor_origem *
fator_origem / fator_destino.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260731_uom_tempo"
down_revision: Union[str, Sequence[str], None] = "20260731_uom_rename"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO unidades_medida
          (id, tenant_id, codigo, nome, dimensao, codigo_referencia, fator_referencia,
           sistema, ativo, casas_decimais, eh_unidade_base)
        VALUES
          (gen_random_uuid(), NULL, 'HORA',   'Hora',   'tempo', 'HORA', 1.000000000,          true, true, 2, true),
          (gen_random_uuid(), NULL, 'DIA',    'Dia',    'tempo', 'HORA', 24.000000000,         true, true, 2, false),
          (gen_random_uuid(), NULL, 'MINUTO', 'Minuto', 'tempo', 'HORA', 0.016666667,          true, true, 4, false)
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM unidades_medida WHERE codigo IN ('HORA', 'DIA', 'MINUTO') AND dimensao = 'tempo'")
