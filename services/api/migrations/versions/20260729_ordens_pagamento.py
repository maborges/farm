"""Cria ordens de pagamento para remessas bancárias.

Revision ID: 20260729_ordens_pagamento
Revises: 20260729_contas_bancarias_remessa
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260729_ordens_pagamento"
down_revision = "20260729_contas_bancarias_remessa"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("fin_ordens_pagamento",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conta_bancaria_id", UUID(as_uuid=True), sa.ForeignKey("fin_contas_bancarias.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("data_pagamento", sa.Date(), nullable=False), sa.Column("banco_codigo", sa.String(3), nullable=False),
        sa.Column("ambiente", sa.String(20), nullable=False), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("sequencial", sa.Integer(), nullable=False), sa.Column("total_valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("arquivo_nome", sa.String(255)), sa.Column("arquivo_hash", sa.String(64)), sa.Column("observacoes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fin_ordens_pagamento_tenant_id", "fin_ordens_pagamento", ["tenant_id"])
    op.create_table("fin_itens_ordem_pagamento",
        sa.Column("id", UUID(as_uuid=True), primary_key=True), sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordem_pagamento_id", UUID(as_uuid=True), sa.ForeignKey("fin_ordens_pagamento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("despesa_id", UUID(as_uuid=True), sa.ForeignKey("fin_despesas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False), sa.Column("forma_pagamento", sa.String(20), nullable=False),
        sa.Column("favorecido_snapshot", sa.String(150), nullable=False), sa.Column("dados_pagamento_snapshot", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("motivo_rejeicao", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fin_itens_ordem_pagamento_tenant_id", "fin_itens_ordem_pagamento", ["tenant_id"])
    op.create_index("ix_fin_itens_ordem_pagamento_ordem", "fin_itens_ordem_pagamento", ["ordem_pagamento_id"])


def downgrade():
    op.drop_table("fin_itens_ordem_pagamento")
    op.drop_table("fin_ordens_pagamento")
