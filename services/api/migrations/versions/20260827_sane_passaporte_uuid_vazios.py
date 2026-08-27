"""Normalize empty UUID values left by legacy passaporte records."""

from alembic import op


revision = "20260827_sane_passaporte_uuid_vazios"
down_revision = "20260826_carbono_lifecycle"
branch_labels = None
depends_on = None


_OPTIONAL_UUID_COLUMNS = (
    "programa_id",
    "propriedade_id",
    "imovel_rural_id",
    "propriedade_imovel_id",
    "lote_rastreabilidade_id",
    "caderno_lote_comercial_id",
    "responsavel_pessoa_id",
    "public_token",
)


def upgrade() -> None:
    """Replace legacy empty UUID strings with SQL NULL values."""
    for column in _OPTIONAL_UUID_COLUMNS:
        op.execute(
            f"UPDATE rastreabilidade_passaportes "
            f"SET {column} = NULL "
            f"WHERE NULLIF({column}::text, '') IS NULL "
            f"AND {column} IS NOT NULL"
        )


def downgrade() -> None:
    """No safe reverse operation exists for normalized legacy values."""
    pass
