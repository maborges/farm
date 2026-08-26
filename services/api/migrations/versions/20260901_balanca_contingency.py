"""Restore the revision marker used by the deployed database.

The deployed database was stamped with this revision, but the original
revision file was missing from the repository.  Keeping the marker available
allows Alembic to resolve the graph and apply subsequent repair migrations.
"""

revision = "20260901_balanca_contingency"
down_revision = "fase3_sprints27_33_final"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Restore the historical revision marker without changing data."""


def downgrade() -> None:
    """Restore the historical revision marker without changing data."""
