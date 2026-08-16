"""depreciacao linear - equipamentos e benfeitorias

Revision ID: 20260816_depreciacao_linear
Revises: 20260815_manutencao_benfeitoria
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260816_depreciacao_linear"
down_revision = "20260815_manutencao_benfeitoria"
branch_labels = None
depends_on = None


def _rebuild_check_constraint(valores: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("cost_allocations")}
    if "ck_cost_allocations_source" in constraints:
        op.drop_constraint("ck_cost_allocations_source", "cost_allocations", type_="check")
    op.create_check_constraint(
        "ck_cost_allocations_source",
        "cost_allocations",
        f"source IN ({valores})",
    )


def upgrade():
    _rebuild_check_constraint(
        "'OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL','PECUARIA_VACINACAO',"
        "'APONTAMENTO_MAO_OBRA','FROTA_APONTAMENTO','FROTA_COMBUSTIVEL','FROTA_PECAS','FROTA_MANUTENCAO',"
        "'RH_DIARIA','RH_EMPREITADA','PERDA_ESTOQUE','DEPRECIACAO_EQUIPAMENTO','DEPRECIACAO_BENFEITORIA'"
    )

    op.add_column(
        "cadastros_equipamentos",
        sa.Column("vida_util_anos", sa.Integer(), nullable=True),
    )
    op.add_column(
        "cadastros_equipamentos",
        sa.Column("valor_residual", sa.Float(), nullable=True),
    )

    op.add_column(
        "imoveis_benfeitorias",
        sa.Column("unidade_produtiva_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "imoveis_benfeitorias",
        sa.Column("vida_util_anos", sa.Integer(), nullable=True),
    )
    op.add_column(
        "imoveis_benfeitorias",
        sa.Column("valor_residual", sa.Numeric(12, 2), nullable=True),
    )
    op.create_index(
        "ix_imoveis_benfeitorias_unidade_produtiva_id",
        "imoveis_benfeitorias",
        ["unidade_produtiva_id"],
    )
    op.create_foreign_key(
        "fk_imoveis_benfeitorias_unidade_produtiva",
        "imoveis_benfeitorias",
        "unidades_produtivas",
        ["unidade_produtiva_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("COMMIT")


def downgrade():
    _rebuild_check_constraint(
        "'OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL','PECUARIA_VACINACAO',"
        "'APONTAMENTO_MAO_OBRA','FROTA_APONTAMENTO','FROTA_COMBUSTIVEL','FROTA_PECAS','FROTA_MANUTENCAO',"
        "'RH_DIARIA','RH_EMPREITADA','PERDA_ESTOQUE'"
    )
    op.drop_constraint(
        "fk_imoveis_benfeitorias_unidade_produtiva",
        "imoveis_benfeitorias",
        type_="foreignkey",
    )
    op.drop_index("ix_imoveis_benfeitorias_unidade_produtiva_id", table_name="imoveis_benfeitorias")
    op.drop_column("imoveis_benfeitorias", "valor_residual")
    op.drop_column("imoveis_benfeitorias", "vida_util_anos")
    op.drop_column("imoveis_benfeitorias", "unidade_produtiva_id")
    op.drop_column("cadastros_equipamentos", "valor_residual")
    op.drop_column("cadastros_equipamentos", "vida_util_anos")
    op.execute("COMMIT")
