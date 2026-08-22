"""Allow integration health alerts in the operational alerts domain."""

from alembic import op
import sqlalchemy as sa


revision = "20260820_alerts_integrations_domain"
down_revision = "20260820_integracoes_rls_safe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_operational_alerts_domain", "operational_alerts", type_="check")
    op.create_check_constraint(
        "ck_operational_alerts_domain",
        "operational_alerts",
        "domain IN ('AGRICULTURE', 'LIVESTOCK', 'FINANCE', 'OPERATIONS', 'FIELD', 'INTEGRATIONS', 'SYSTEM')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_operational_alerts_domain", "operational_alerts", type_="check")
    op.create_check_constraint(
        "ck_operational_alerts_domain",
        "operational_alerts",
        "domain IN ('AGRICULTURE', 'LIVESTOCK', 'FINANCE', 'OPERATIONS', 'FIELD', 'SYSTEM')",
    )
