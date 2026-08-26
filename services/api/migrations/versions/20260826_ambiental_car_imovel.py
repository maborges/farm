"""Link Ambiental CAR records to their canonical rural property."""

from alembic import op
import sqlalchemy as sa


revision = "20260826_ambiental_car_imovel"
down_revision = "20260826_ambiental_unidade_obrigatoria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the canonical rural-property reference, preserving legacy records."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("amb_registros_car")}
    if "imovel_rural_id" not in columns:
        op.add_column(
            "amb_registros_car",
            sa.Column("imovel_rural_id", sa.Uuid(), nullable=True),
        )
        op.create_index(
            "ix_amb_registros_car_imovel_rural_id",
            "amb_registros_car",
            ["imovel_rural_id"],
        )
        op.create_foreign_key(
            "fk_amb_registros_car_imovel_rural_id",
            "amb_registros_car",
            "imoveis_rurais",
            ["imovel_rural_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    """Remove the property reference while retaining the CAR records."""
    op.drop_constraint("fk_amb_registros_car_imovel_rural_id", "amb_registros_car", type_="foreignkey")
    op.drop_index("ix_amb_registros_car_imovel_rural_id", table_name="amb_registros_car")
    op.drop_column("amb_registros_car", "imovel_rural_id")
