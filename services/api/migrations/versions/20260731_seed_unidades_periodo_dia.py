"""Seed de unidades de período do dia (MANHA, TARDE, NOITE) — 8h cada

Revision ID: 20260731_uom_periodo
Revises: 20260731_uom_tempo2
Create Date: 2026-07-31

Aditivo: completa a dimensão 'tempo' com os 3 turnos fixos de 8h cada
(convenção definida pelo usuário: manhã/tarde/noite = 24h / 3 turnos),
convertíveis com o restante da dimensão via fator_referencia (base HORA).
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260731_uom_periodo"
down_revision: Union[str, Sequence[str], None] = "20260731_uom_tempo2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO unidades_medida
          (id, tenant_id, codigo, nome, dimensao, codigo_referencia, fator_referencia,
           sistema, ativo, casas_decimais, eh_unidade_base)
        VALUES
          (gen_random_uuid(), NULL, 'MANHA', 'Manhã (turno de 8h)', 'tempo', 'HORA', 8.000000000, true, true, 0, false),
          (gen_random_uuid(), NULL, 'TARDE', 'Tarde (turno de 8h)', 'tempo', 'HORA', 8.000000000, true, true, 0, false),
          (gen_random_uuid(), NULL, 'NOITE', 'Noite (turno de 8h)', 'tempo', 'HORA', 8.000000000, true, true, 0, false)
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM unidades_medida WHERE codigo IN ('MANHA', 'TARDE', 'NOITE') AND dimensao = 'tempo'")
