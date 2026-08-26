"""Materialize cadastral CAR records with explicit SICAR provenance."""

from alembic import op
import sqlalchemy as sa


revision = "20260826_ambiental_car_provenance"
down_revision = "20260826_ambiental_car_imovel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add provenance fields and materialize CARs already present on rural properties."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("amb_registros_car")}
    if "origem_dados" not in columns:
        op.add_column("amb_registros_car", sa.Column("origem_dados", sa.String(30), nullable=False, server_default="MANUAL"))
    if "situacao_sicar" not in columns:
        op.add_column("amb_registros_car", sa.Column("situacao_sicar", sa.String(30), nullable=False, server_default="NAO_CONSULTADO"))
    if "data_ultima_consulta_sicar" not in columns:
        op.add_column("amb_registros_car", sa.Column("data_ultima_consulta_sicar", sa.Date(), nullable=True))

    op.alter_column("amb_registros_car", "origem_dados", nullable=False, server_default="MANUAL")
    op.alter_column("amb_registros_car", "situacao_sicar", nullable=False, server_default="NAO_CONSULTADO")
    op.create_index(
        "uq_amb_registros_car_tenant_imovel",
        "amb_registros_car",
        ["tenant_id", "imovel_rural_id"],
        unique=True,
        postgresql_where=sa.text("imovel_rural_id IS NOT NULL"),
    )
def downgrade() -> None:
    """Remove provenance metadata and the materialization uniqueness guard."""
    op.drop_index("uq_amb_registros_car_tenant_imovel", table_name="amb_registros_car")
    op.drop_column("amb_registros_car", "data_ultima_consulta_sicar")
    op.drop_column("amb_registros_car", "situacao_sicar")
    op.drop_column("amb_registros_car", "origem_dados")
