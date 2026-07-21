"""Tornar identificadores externos Sankhya únicos por tenant.

Revision ID: 20260718_sankhya_tenant_keys
Revises: tenant_fk_repair_01d
Create Date: 2026-07-18

Preserva os dados legados e troca unicidade global por chaves compostas,
permitindo que tenants distintos usem os mesmos códigos do ERP.
"""

from alembic import op

revision = "20260718_sankhya_tenant_keys"
down_revision = "tenant_fk_repair_01d"
branch_labels = None
depends_on = None

SCHEMA = "farms"
INDEXES = (
    ("sankhya_pessoas", "sankhya_id", "ix_sankhya_pessoas_sankhya_id"),
    ("sankhya_produtos", "sankhya_id", "ix_sankhya_produtos_sankhya_id"),
    ("sankhya_nfe", "sankhya_id", "ix_sankhya_nfe_sankhya_id"),
    ("sankhya_nfe", "chave_acesso", "ix_sankhya_nfe_chave_acesso"),
    (
        "sankhya_lancamentos_financeiros",
        "sankhya_id",
        "ix_sankhya_lancamentos_financeiros_sankhya_id",
    ),
)
CONSTRAINTS = (
    ("sankhya_pessoas", ("tenant_id", "sankhya_id"), "uq_sankhya_pessoas_tenant_external"),
    ("sankhya_produtos", ("tenant_id", "sankhya_id"), "uq_sankhya_produtos_tenant_external"),
    ("sankhya_nfe", ("tenant_id", "sankhya_id"), "uq_sankhya_nfe_tenant_external"),
    ("sankhya_nfe", ("tenant_id", "chave_acesso"), "uq_sankhya_nfe_tenant_access_key"),
    (
        "sankhya_lancamentos_financeiros",
        ("tenant_id", "sankhya_id"),
        "uq_sankhya_lancamentos_tenant_external",
    ),
)


def upgrade() -> None:
    """Substituir índices únicos globais por constraints compostas tenant-safe."""
    for table_name, column_name, index_name in INDEXES:
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
        op.create_index(index_name, table_name, [column_name], unique=False, schema=SCHEMA)
    for table_name, columns, constraint_name in CONSTRAINTS:
        op.create_unique_constraint(constraint_name, table_name, list(columns), schema=SCHEMA)


def downgrade() -> None:
    """Restaurar a unicidade global original quando os dados ainda permitirem."""
    for table_name, _, constraint_name in reversed(CONSTRAINTS):
        op.drop_constraint(constraint_name, table_name, type_="unique", schema=SCHEMA)
    for table_name, column_name, index_name in reversed(INDEXES):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
        op.create_index(index_name, table_name, [column_name], unique=True, schema=SCHEMA)
