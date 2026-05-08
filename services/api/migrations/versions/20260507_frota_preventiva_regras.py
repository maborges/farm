"""add frota preventiva rule fields

Revision ID: 20260507_frota_preventiva
Revises: 20260505_produtos_global
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260507_frota_preventiva"
down_revision = "20260505_produtos_global"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    plano_columns = {column["name"] for column in inspector.get_columns("frota_planos_manutencao")}
    if "frequencia_dias" not in plano_columns:
        op.add_column("frota_planos_manutencao", sa.Column("frequencia_dias", sa.Integer(), nullable=True))
    if "ultimo_registro_data" not in plano_columns:
        op.add_column(
            "frota_planos_manutencao",
            sa.Column("ultimo_registro_data", sa.DateTime(timezone=True), nullable=True),
        )
    if "created_at" not in plano_columns:
        op.add_column(
            "frota_planos_manutencao",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    os_columns = {column["name"] for column in inspector.get_columns("frota_ordens_servico")}
    if "plano_manutencao_id" not in os_columns:
        op.add_column(
            "frota_ordens_servico",
            sa.Column("plano_manutencao_id", sa.Uuid(), nullable=True),
        )
        op.create_index(
            op.f("ix_frota_ordens_servico_plano_manutencao_id"),
            "frota_ordens_servico",
            ["plano_manutencao_id"],
            unique=False,
        )
        op.create_foreign_key(
            op.f("frota_ordens_servico_plano_manutencao_id_fkey"),
            "frota_ordens_servico",
            "frota_planos_manutencao",
            ["plano_manutencao_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    os_columns = {column["name"] for column in inspector.get_columns("frota_ordens_servico")}
    if "plano_manutencao_id" in os_columns:
        fk_names = {fk["name"] for fk in inspector.get_foreign_keys("frota_ordens_servico")}
        if op.f("frota_ordens_servico_plano_manutencao_id_fkey") in fk_names:
            op.drop_constraint(
                op.f("frota_ordens_servico_plano_manutencao_id_fkey"),
                "frota_ordens_servico",
                type_="foreignkey",
            )
        index_names = {idx["name"] for idx in inspector.get_indexes("frota_ordens_servico")}
        if op.f("ix_frota_ordens_servico_plano_manutencao_id") in index_names:
            op.drop_index(op.f("ix_frota_ordens_servico_plano_manutencao_id"), table_name="frota_ordens_servico")
        op.drop_column("frota_ordens_servico", "plano_manutencao_id")

    plano_columns = {column["name"] for column in inspector.get_columns("frota_planos_manutencao")}
    if "created_at" in plano_columns:
        op.drop_column("frota_planos_manutencao", "created_at")
    if "ultimo_registro_data" in plano_columns:
        op.drop_column("frota_planos_manutencao", "ultimo_registro_data")
    if "frequencia_dias" in plano_columns:
        op.drop_column("frota_planos_manutencao", "frequencia_dias")
