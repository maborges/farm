"""Add idempotency constraints to climate observations and forecasts."""

from alembic import op
import sqlalchemy as sa


revision = "20260820_clima_idempotency"
down_revision = "69b1123a3e0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep one deterministic row when historical retries already produced duplicates.
    op.execute(
        sa.text(
            """
            DELETE FROM registros_clima duplicate
            USING registros_clima original
            WHERE duplicate.tenant_id = original.tenant_id
              AND duplicate.unidade_produtiva_id = original.unidade_produtiva_id
              AND duplicate.data_registro = original.data_registro
              AND duplicate.fonte = original.fonte
              AND duplicate.id > original.id
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM previsoes_clima duplicate
            USING previsoes_clima original
            WHERE duplicate.tenant_id = original.tenant_id
              AND duplicate.unidade_produtiva_id = original.unidade_produtiva_id
              AND duplicate.data_previsao = original.data_previsao
              AND duplicate.id > original.id
            """
        )
    )
    op.create_unique_constraint(
        "uq_registros_clima_tenant_unidade_data_fonte",
        "registros_clima",
        ["tenant_id", "unidade_produtiva_id", "data_registro", "fonte"],
    )
    op.create_unique_constraint(
        "uq_previsoes_clima_tenant_unidade_data",
        "previsoes_clima",
        ["tenant_id", "unidade_produtiva_id", "data_previsao"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_previsoes_clima_tenant_unidade_data", "previsoes_clima", type_="unique")
    op.drop_constraint("uq_registros_clima_tenant_unidade_data_fonte", "registros_clima", type_="unique")
