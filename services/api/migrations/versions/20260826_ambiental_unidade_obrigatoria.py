"""Require every operational Ambiental record to identify its farm."""

from alembic import op
import sqlalchemy as sa


revision = "20260826_ambiental_unidade_obrigatoria"
down_revision = "20260826_merge_operational_heads"
branch_labels = None
depends_on = None

TABLES = ("amb_registros_car", "amb_alertas", "amb_outorgas_hidricas")


def upgrade() -> None:
    """Make the operational farm context mandatory after validating data."""
    bind = op.get_bind()
    for table_name in TABLES:
        missing = bind.execute(
            sa.text(
                f'SELECT count(*) FROM "{table_name}" '
                "WHERE unidade_produtiva_id IS NULL"
            )
        ).scalar_one()
        if missing:
            raise RuntimeError(
                f"{table_name} possui {missing} registro(s) sem unidade_produtiva_id; "
                "corrija o vínculo antes de aplicar a obrigatoriedade."
            )
        op.alter_column(table_name, "unidade_produtiva_id", nullable=False)


def downgrade() -> None:
    """Restore nullable columns for rollback compatibility."""
    for table_name in TABLES:
        op.alter_column(table_name, "unidade_produtiva_id", nullable=True)
