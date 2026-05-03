"""step38 — ia_checkout: valor_estimado, link_pagamento, status_pagamento

Revision ID: step38_ia_checkout
Revises: step37_billing_sol
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "step38_ia_checkout"
down_revision = "step37_billing_sol"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column("valor_estimado", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column("link_pagamento", sa.String(500), nullable=True),
    )
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column(
            "status_pagamento",
            sa.String(20),
            nullable=True,
            server_default="PENDENTE",
        ),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_column("billing_solicitacoes_comerciais", "status_pagamento")
    op.drop_column("billing_solicitacoes_comerciais", "link_pagamento")
    op.drop_column("billing_solicitacoes_comerciais", "valor_estimado")
