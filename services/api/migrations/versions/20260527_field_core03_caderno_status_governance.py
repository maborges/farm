"""field_core03_caderno_status_governance

Revision ID: 20260527_field_core03
Revises: 20260527_field_core02
Create Date: 2026-05-27 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260527_field_core03"
down_revision: Union[str, Sequence[str], None] = "20260527_field_core02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("caderno_evento_status_historico"):
        op.create_table(
            "caderno_evento_status_historico",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column("caderno_entrada_id", sa.Uuid(), nullable=False),
            sa.Column("status_anterior", sa.String(length=30), nullable=True),
            sa.Column("status_novo", sa.String(length=30), nullable=False),
            sa.Column("usuario_id", sa.Uuid(), nullable=True),
            sa.Column("justificativa", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["caderno_entrada_id"], ["caderno_campo_entradas.id"], ondelete="CASCADE"),
        )

    existing_indexes = {
        index["name"] for index in inspector.get_indexes("caderno_evento_status_historico")
    }
    if "ix_caderno_evento_status_entrada" not in existing_indexes:
        op.create_index(
            "ix_caderno_evento_status_entrada",
            "caderno_evento_status_historico",
            ["caderno_entrada_id"],
        )
    if "ix_caderno_evento_status_novo" not in existing_indexes:
        op.create_index(
            "ix_caderno_evento_status_novo",
            "caderno_evento_status_historico",
            ["status_novo"],
        )

    rows = bind.execute(
        sa.text(
            """
            SELECT id, tenant_id, status_evento, usuario_id, justificativa_retroativa
              FROM caderno_campo_entradas
             ORDER BY created_at ASC
            """
        )
    ).mappings().all()

    for row in rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO caderno_evento_status_historico
                    (id, tenant_id, caderno_entrada_id, status_anterior, status_novo, usuario_id, justificativa, created_at)
                SELECT
                    :id, :tenant_id, :caderno_entrada_id, NULL, :status_novo, :usuario_id, :justificativa, NOW()
                WHERE NOT EXISTS (
                    SELECT 1
                      FROM caderno_evento_status_historico
                     WHERE caderno_entrada_id = :caderno_entrada_id
                )
                """
            ),
            {
                "id": uuid.uuid4(),
                "tenant_id": row["tenant_id"],
                "caderno_entrada_id": row["id"],
                "status_novo": row["status_evento"] or "CONSOLIDADO",
                "usuario_id": row["usuario_id"],
                "justificativa": row["justificativa_retroativa"],
            },
        )


def downgrade() -> None:
    op.drop_index("ix_caderno_evento_status_novo", table_name="caderno_evento_status_historico")
    op.drop_index("ix_caderno_evento_status_entrada", table_name="caderno_evento_status_historico")
    op.drop_table("caderno_evento_status_historico")
