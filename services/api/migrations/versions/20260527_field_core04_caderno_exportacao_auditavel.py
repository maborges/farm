"""field_core04_caderno_exportacao_auditavel

Revision ID: 20260527_field_core04
Revises: 20260527_field_core03
Create Date: 2026-05-27 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "20260527_field_core04"
down_revision: Union[str, Sequence[str], None] = "20260527_field_core03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("caderno_exportacoes")}

    if "modo_exportacao" not in columns:
        op.add_column(
            "caderno_exportacoes",
            sa.Column("modo_exportacao", sa.String(length=20), nullable=False, server_default=sa.text("'OFICIAL'")),
        )
    if "hash_documental" not in columns:
        op.add_column("caderno_exportacoes", sa.Column("hash_documental", sa.String(length=128), nullable=True))
    if "assinatura_hash" not in columns:
        op.add_column("caderno_exportacoes", sa.Column("assinatura_hash", sa.String(length=128), nullable=True))
    if "responsavel_tecnico_id" not in columns:
        op.add_column("caderno_exportacoes", sa.Column("responsavel_tecnico_id", sa.Uuid(), nullable=True))
    if "responsavel_tecnico_nome" not in columns:
        op.add_column("caderno_exportacoes", sa.Column("responsavel_tecnico_nome", sa.String(length=200), nullable=True))
    if "responsavel_tecnico_crea" not in columns:
        op.add_column("caderno_exportacoes", sa.Column("responsavel_tecnico_crea", sa.String(length=30), nullable=True))
    if "assinado_em" not in columns:
        op.add_column("caderno_exportacoes", sa.Column("assinado_em", sa.DateTime(timezone=True), nullable=True))
    if "assinatura_origem" not in columns:
        op.add_column("caderno_exportacoes", sa.Column("assinatura_origem", sa.String(length=40), nullable=True))
    if "observacao_assinatura" not in columns:
        op.add_column("caderno_exportacoes", sa.Column("observacao_assinatura", sa.Text(), nullable=True))

    bind.execute(
        sa.text(
            """
            UPDATE caderno_exportacoes
               SET modo_exportacao = COALESCE(modo_exportacao, 'OFICIAL'),
                   responsavel_tecnico_nome = COALESCE(responsavel_tecnico_nome, assinado_por),
                   responsavel_tecnico_crea = COALESCE(responsavel_tecnico_crea, crea_rt),
                   assinado_em = COALESCE(assinado_em, data_geracao),
                   assinatura_origem = COALESCE(assinatura_origem, CASE WHEN assinado_por IS NOT NULL THEN 'LEGACY' ELSE NULL END)
             WHERE modo_exportacao IS NULL
                OR responsavel_tecnico_nome IS NULL
                OR responsavel_tecnico_crea IS NULL
                OR assinado_em IS NULL
                OR assinatura_origem IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("caderno_exportacoes", "observacao_assinatura")
    op.drop_column("caderno_exportacoes", "assinatura_origem")
    op.drop_column("caderno_exportacoes", "assinado_em")
    op.drop_column("caderno_exportacoes", "responsavel_tecnico_crea")
    op.drop_column("caderno_exportacoes", "responsavel_tecnico_nome")
    op.drop_column("caderno_exportacoes", "responsavel_tecnico_id")
    op.drop_column("caderno_exportacoes", "assinatura_hash")
    op.drop_column("caderno_exportacoes", "hash_documental")
    op.drop_column("caderno_exportacoes", "modo_exportacao")
