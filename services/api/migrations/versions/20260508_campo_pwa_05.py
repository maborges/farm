"""campo pwa 05 — tarefas programadas

Revision ID: 20260508_campo_pwa_05
Revises: 20260508_campo_pwa
Create Date: 2026-05-08
"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260508_campo_pwa_05"
down_revision: Union[str, Sequence[str], None] = "20260508_campo_pwa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campo_tarefas", sa.Column("origem", sa.String(20), nullable=False, server_default="MANUAL"))
    op.add_column("campo_tarefas", sa.Column("status_execucao", sa.String(20), nullable=False, server_default="PENDENTE"))
    op.add_column("campo_tarefas", sa.Column("data_programada", sa.Date(), nullable=True))
    op.add_column("campo_tarefas", sa.Column("prioridade", sa.String(10), nullable=False, server_default="NORMAL"))
    op.add_column("campo_tarefas", sa.Column("operador_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("campo_tarefas", sa.Column("titulo", sa.String(200), nullable=True))
    op.add_column("campo_tarefas", sa.Column("iniciada_em", sa.DateTime(), nullable=True))
    op.add_column("campo_tarefas", sa.Column("concluida_em", sa.DateTime(), nullable=True))

    # Tarefas manuais já existentes = concluídas
    op.execute("UPDATE campo_tarefas SET status_execucao = 'CONCLUIDA' WHERE origem = 'MANUAL'")

    op.create_index("ix_ct_fazenda_data", "campo_tarefas", ["tenant_id", "data_programada", "status_execucao"])
    op.create_index("ix_ct_operador", "campo_tarefas", ["operador_id", "status_execucao"])
    op.create_index("ix_ct_dispositivo_data", "campo_tarefas", ["dispositivo_id", "data_programada"])

    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_index("ix_ct_dispositivo_data", "campo_tarefas")
    op.drop_index("ix_ct_operador", "campo_tarefas")
    op.drop_index("ix_ct_fazenda_data", "campo_tarefas")
    op.drop_column("campo_tarefas", "concluida_em")
    op.drop_column("campo_tarefas", "iniciada_em")
    op.drop_column("campo_tarefas", "titulo")
    op.drop_column("campo_tarefas", "operador_id")
    op.drop_column("campo_tarefas", "prioridade")
    op.drop_column("campo_tarefas", "data_programada")
    op.drop_column("campo_tarefas", "status_execucao")
    op.drop_column("campo_tarefas", "origem")
