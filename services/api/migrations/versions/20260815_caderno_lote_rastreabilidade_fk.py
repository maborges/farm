"""adiciona FK opcional CadernoLoteComercial.lote_rastreabilidade_id -> lotes_rastreabilidade

OPERATIONS-GAP-01 §21.11: LoteRastreabilidade (lote de campo, safra+talhão) e
CadernoLoteComercial (passaporte comercial assinado) são conceitos legítimos e
desconectados — sem essa FK, o mesmo lote físico podia aparecer sem elo formal
em duas telas diferentes. Coluna nullable, sem backfill (nenhum vínculo é
inferível automaticamente; preenchimento é manual, quando fizer sentido).

Revision ID: 20260815_caderno_lote_rastreab_fk
Revises: 20260815_prescricoes_vra_schema
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_caderno_lote_rastreab_fk"
down_revision = "20260815_prescricoes_vra_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "caderno_lotes_comerciais",
        sa.Column("lote_rastreabilidade_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_caderno_lote_comercial_lote_rastreabilidade",
        "caderno_lotes_comerciais",
        "lotes_rastreabilidade",
        ["lote_rastreabilidade_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_caderno_lotes_comerciais_lote_rastreabilidade_id",
        "caderno_lotes_comerciais",
        ["lote_rastreabilidade_id"],
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_index("ix_caderno_lotes_comerciais_lote_rastreabilidade_id", table_name="caderno_lotes_comerciais")
    op.drop_constraint("fk_caderno_lote_comercial_lote_rastreabilidade", "caderno_lotes_comerciais", type_="foreignkey")
    op.drop_column("caderno_lotes_comerciais", "lote_rastreabilidade_id")
    op.execute("COMMIT")
