"""Separate environmental farm context from legacy agricultural production unit."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260826_carbono_unidade_produtiva"
down_revision = "20260826_ambiental_car_provenance"
branch_labels = None
depends_on = None

TABLES = ("carbono_emissoes", "carbono_projetos")


def _columns(table_name: str) -> set[str]:
    """Return columns for an existing table."""
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    """Add the canonical farm relation and preserve the agricultural relation."""
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())
    for table_name in TABLES:
        if table_name not in existing_tables:
            continue
        columns = _columns(table_name)
        if "unidade_produtiva_id" in columns and "production_unit_id" not in columns:
            op.alter_column(table_name, "unidade_produtiva_id", new_column_name="production_unit_id")
        if "unidade_produtiva_id" not in _columns(table_name):
            op.add_column(table_name, sa.Column("unidade_produtiva_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"fk_{table_name}_unidade_produtiva",
            table_name,
            "unidades_produtivas",
            ["unidade_produtiva_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table_name}_unidade_produtiva_id", table_name, ["unidade_produtiva_id"])
        op.execute(sa.text(f"""
            UPDATE {table_name} AS carbono
            SET unidade_produtiva_id = area.unidade_produtiva_id
            FROM production_units AS unidade
            JOIN cadastros_areas_rurais AS area ON area.id = unidade.area_id
            WHERE carbono.production_unit_id = unidade.id
              AND carbono.unidade_produtiva_id IS NULL
        """))


def downgrade() -> None:
    """Restore the previous column name and remove the canonical farm relation."""
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())
    for table_name in TABLES:
        if table_name not in existing_tables:
            continue
        op.drop_index(f"ix_{table_name}_unidade_produtiva_id", table_name=table_name)
        op.drop_constraint(f"fk_{table_name}_unidade_produtiva", table_name=table_name, type_="foreignkey")
        op.drop_column(table_name, "unidade_produtiva_id")
        op.alter_column(table_name, "production_unit_id", new_column_name="unidade_produtiva_id")
