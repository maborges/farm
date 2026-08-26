"""Converge the active Ambiental and Pecuaria migration heads."""


revision = "20260826_merge_operational_heads"
down_revision = (
    "20260824_pecuaria_species_defaults",
    "20260826_ambiental_foundation",
    "24e6a080f3b3",
    "a1b2c3d4e5f7",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Record convergence of the two active module branches."""


def downgrade() -> None:
    """Re-expose the two module heads when downgrading."""
