"""Align climate intelligence model tables with the tenant-aware ORM models."""

from alembic import op
import sqlalchemy as sa


revision = "20260823_clima_inteligencia_integrity"
down_revision = "b3e8dc35c257"
branch_labels = None
depends_on = None


def _tenant_expr() -> str:
    return "tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), '')"


def _enable_model_rls(table: str, policy: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    for action in ("select", "insert", "update", "delete"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy}_{action} ON {table}"))
    expr = _tenant_expr()
    op.execute(sa.text(f"CREATE POLICY {policy}_select ON {table} FOR SELECT USING ({expr} OR tenant_id IS NULL)"))
    op.execute(sa.text(f"CREATE POLICY {policy}_insert ON {table} FOR INSERT WITH CHECK ({expr} OR tenant_id IS NULL)"))
    op.execute(sa.text(f"CREATE POLICY {policy}_update ON {table} FOR UPDATE USING ({expr} OR tenant_id IS NULL) WITH CHECK ({expr} OR tenant_id IS NULL)"))
    op.execute(sa.text(f"CREATE POLICY {policy}_delete ON {table} FOR DELETE USING ({expr} OR tenant_id IS NULL)"))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("modelos_fitossanitarios")}
    if "tenant_id" not in columns:
        op.add_column(
            "modelos_fitossanitarios",
            sa.Column("tenant_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_modelos_fitossanitarios_tenant_id",
            "modelos_fitossanitarios",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index("ix_modelos_fitossanitarios_tenant_id", "modelos_fitossanitarios", ["tenant_id"])

    if "is_global" not in columns:
        op.add_column(
            "modelos_fitossanitarios",
            sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    op.drop_constraint("uq_modelos_fito_cultura_doenca", "modelos_fitossanitarios", type_="unique")
    op.create_index(
        "uq_modelos_fito_global_cultura_doenca",
        "modelos_fitossanitarios",
        ["cultura", "doenca"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )
    op.create_index(
        "uq_modelos_fito_tenant_cultura_doenca",
        "modelos_fitossanitarios",
        ["tenant_id", "cultura", "doenca"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )
    _enable_model_rls("modelos_fitossanitarios", "modelos_fitossanitarios")
    op.drop_constraint("uq_modelos_zoo_especie_risco", "modelos_zoosanitarios", type_="unique")
    op.create_index(
        "uq_modelos_zoo_global_especie_risco",
        "modelos_zoosanitarios",
        ["especie", "tipo_risco"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )
    op.create_index(
        "uq_modelos_zoo_tenant_especie_risco",
        "modelos_zoosanitarios",
        ["tenant_id", "especie", "tipo_risco"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )
    _enable_model_rls("modelos_zoosanitarios", "modelos_zoosanitarios")


def downgrade() -> None:
    for table, policy in (("modelos_zoosanitarios", "modelos_zoosanitarios"), ("modelos_fitossanitarios", "modelos_fitossanitarios")):
        for action in ("select", "insert", "update", "delete"):
            op.execute(sa.text(f"DROP POLICY IF EXISTS {policy}_{action} ON {table}"))
        op.execute(sa.text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    op.drop_index("uq_modelos_zoo_tenant_especie_risco", table_name="modelos_zoosanitarios")
    op.drop_index("uq_modelos_zoo_global_especie_risco", table_name="modelos_zoosanitarios")
    op.create_unique_constraint("uq_modelos_zoo_especie_risco", "modelos_zoosanitarios", ["tenant_id", "especie", "tipo_risco"])
    op.drop_index("uq_modelos_fito_tenant_cultura_doenca", table_name="modelos_fitossanitarios")
    op.drop_index("uq_modelos_fito_global_cultura_doenca", table_name="modelos_fitossanitarios")
    op.create_unique_constraint("uq_modelos_fito_cultura_doenca", "modelos_fitossanitarios", ["cultura", "doenca"])
    op.drop_column("modelos_fitossanitarios", "is_global")
    op.drop_index("ix_modelos_fitossanitarios_tenant_id", table_name="modelos_fitossanitarios")
    op.drop_constraint("fk_modelos_fitossanitarios_tenant_id", "modelos_fitossanitarios", type_="foreignkey")
    op.drop_column("modelos_fitossanitarios", "tenant_id")
