"""Seed de unidades de tempo adicionais (SEGUNDO, SEMANA, MES, ANO)

Revision ID: 20260731_uom_tempo2
Revises: 20260731_uom_tempo
Create Date: 2026-07-31

Aditivo: completa a dimensão 'tempo' (base HORA, já seedada em
20260731_uom_tempo) com as unidades restantes solicitadas pelo usuário.
Fatores em relação a HORA (unidade-base):
  SEGUNDO -> 0.000277778 (1s = 1/3600h)
  SEMANA  -> 168          (7 dias)
  MES     -> 720          (convenção: 30 dias)
  ANO     -> 8760         (convenção: 365 dias)
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260731_uom_tempo2"
down_revision: Union[str, Sequence[str], None] = "20260731_uom_tempo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO unidades_medida
          (id, tenant_id, codigo, nome, dimensao, codigo_referencia, fator_referencia,
           sistema, ativo, casas_decimais, eh_unidade_base)
        VALUES
          (gen_random_uuid(), NULL, 'SEGUNDO', 'Segundo', 'tempo', 'HORA', 0.000277778, true, true, 0, false),
          (gen_random_uuid(), NULL, 'SEMANA',  'Semana',  'tempo', 'HORA', 168.000000000, true, true, 0, false),
          (gen_random_uuid(), NULL, 'MES',     'Mês',     'tempo', 'HORA', 720.000000000, true, true, 0, false),
          (gen_random_uuid(), NULL, 'ANO',     'Ano',     'tempo', 'HORA', 8760.000000000, true, true, 0, false)
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM unidades_medida WHERE codigo IN ('SEGUNDO', 'SEMANA', 'MES', 'ANO') AND dimensao = 'tempo'")
