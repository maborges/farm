"""frota_step02_add_safra_talhao_to_frota_tables

Revision ID: 20260520_frota_step02
Revises: 6465fa549b71
Create Date: 2026-05-20 00:00:00.000000

Step 02 — Frota: adiciona colunas safra_id e talhao_id nas tabelas de
operacional da frota para congelar o contexto agrícola no momento da
operação (OS, manutenção, abastecimento, apontamentos).

Retrocompatível: todas as colunas são nullable, sem default, sem remoção
de dados existentes.

Tabelas afetadas:
  - frota_registros_manutencao (+ safra_id, talhao_id)
  - frota_abastecimentos       (+ safra_id, talhao_id)
  - frota_ordens_servico       (+ safra_id, talhao_id)
  - frota_apontamentos_uso     (+ safra_id)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260520_frota_step02"
down_revision = "6465fa549b71"
branch_labels = None
depends_on = None

_SCHEMA = "farms"


def _add_safra_talhao(table: str, add_talhao: bool = True) -> None:
    """Adiciona safra_id (e opcionalmente talhao_id) a uma tabela da Frota."""
    with op.batch_alter_table(table, schema=_SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("safra_id", sa.UUID(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table}_safra",
            "safras",
            ["safra_id"],
            ["id"],
            ondelete="SET NULL",
            source_schema=_SCHEMA,
            referent_schema=_SCHEMA,
        )
        batch_op.create_index(f"ix_{table}_safra_id", ["safra_id"])

        if add_talhao:
            batch_op.add_column(sa.Column("talhao_id", sa.UUID(as_uuid=True), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table}_talhao",
                "cadastros_areas_rurais",
                ["talhao_id"],
                ["id"],
                ondelete="SET NULL",
                source_schema=_SCHEMA,
                referent_schema=_SCHEMA,
            )
            batch_op.create_index(f"ix_{table}_talhao_id", ["talhao_id"])


def _drop_safra_talhao(table: str, add_talhao: bool = True) -> None:
    with op.batch_alter_table(table, schema=_SCHEMA) as batch_op:
        if add_talhao:
            batch_op.drop_index(f"ix_{table}_talhao_id")
            batch_op.drop_constraint(f"fk_{table}_talhao", type_="foreignkey")
            batch_op.drop_column("talhao_id")
        batch_op.drop_index(f"ix_{table}_safra_id")
        batch_op.drop_constraint(f"fk_{table}_safra", type_="foreignkey")
        batch_op.drop_column("safra_id")


def upgrade() -> None:
    _add_safra_talhao("frota_registros_manutencao", add_talhao=True)
    _add_safra_talhao("frota_abastecimentos", add_talhao=True)
    _add_safra_talhao("frota_ordens_servico", add_talhao=True)
    _add_safra_talhao("frota_apontamentos_uso", add_talhao=False)


def downgrade() -> None:
    _drop_safra_talhao("frota_apontamentos_uso", add_talhao=False)
    _drop_safra_talhao("frota_ordens_servico", add_talhao=True)
    _drop_safra_talhao("frota_abastecimentos", add_talhao=True)
    _drop_safra_talhao("frota_registros_manutencao", add_talhao=True)
