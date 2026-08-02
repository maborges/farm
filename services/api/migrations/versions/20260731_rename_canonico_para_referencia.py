"""Renomeia terminologia "canônico" para termos de negócio em unidades_medida

Revision ID: 20260731_uom_rename
Revises: 20260731_uom_fk
Create Date: 2026-07-31

Rename puro de colunas/constraints/índices, sem mudança de dado ou tipo:
  - codigo_canonico -> codigo_referencia
  - fator_canonico  -> fator_referencia
  - eh_canonica     -> eh_unidade_base

Motivo: "canônico" é jargão técnico pouco claro para quem administra o
catálogo de unidades; "referência"/"unidade base" comunica melhor o
conceito de negócio (a unidade usada como base de conversão da dimensão).
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260731_uom_rename"
down_revision: Union[str, Sequence[str], None] = "20260731_uom_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("unidades_medida", "codigo_canonico", new_column_name="codigo_referencia")
    op.alter_column("unidades_medida", "fator_canonico", new_column_name="fator_referencia")
    op.alter_column("unidades_medida", "eh_canonica", new_column_name="eh_unidade_base")

    op.drop_constraint("ck_unidades_medida_fator_canonico_positivo", "unidades_medida", type_="check")
    op.create_check_constraint(
        "ck_unidades_medida_fator_referencia_positivo",
        "unidades_medida",
        "fator_referencia > 0",
    )

    op.drop_constraint("ck_unidades_medida_canonica_coerencia", "unidades_medida", type_="check")
    op.create_check_constraint(
        "ck_unidades_medida_referencia_coerencia",
        "unidades_medida",
        "(eh_unidade_base = false) OR (codigo = codigo_referencia AND fator_referencia = 1)",
    )

    op.execute("DROP INDEX IF EXISTS uq_unidades_medida_canonica_global")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_unidades_medida_base_global
          ON unidades_medida (dimensao)
          WHERE eh_unidade_base = true AND tenant_id IS NULL
        """
    )
    op.execute("DROP INDEX IF EXISTS uq_unidades_medida_canonica_tenant")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_unidades_medida_base_tenant
          ON unidades_medida (tenant_id, dimensao)
          WHERE eh_unidade_base = true AND tenant_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_unidades_medida_base_tenant")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_unidades_medida_canonica_tenant
          ON unidades_medida (tenant_id, dimensao)
          WHERE eh_canonica = true AND tenant_id IS NOT NULL
        """
    )
    op.execute("DROP INDEX IF EXISTS uq_unidades_medida_base_global")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_unidades_medida_canonica_global
          ON unidades_medida (dimensao)
          WHERE eh_canonica = true AND tenant_id IS NULL
        """
    )

    op.drop_constraint("ck_unidades_medida_referencia_coerencia", "unidades_medida", type_="check")
    op.create_check_constraint(
        "ck_unidades_medida_canonica_coerencia",
        "unidades_medida",
        "(eh_canonica = false) OR (codigo = codigo_canonico AND fator_canonico = 1)",
    )

    op.drop_constraint("ck_unidades_medida_fator_referencia_positivo", "unidades_medida", type_="check")
    op.create_check_constraint(
        "ck_unidades_medida_fator_canonico_positivo",
        "unidades_medida",
        "fator_canonico > 0",
    )

    op.alter_column("unidades_medida", "eh_unidade_base", new_column_name="eh_canonica")
    op.alter_column("unidades_medida", "fator_referencia", new_column_name="fator_canonico")
    op.alter_column("unidades_medida", "codigo_referencia", new_column_name="codigo_canonico")
