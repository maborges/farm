"""Unifica a baseline de instalação e a cadeia operacional atual."""

from typing import Sequence, Union


revision: str = "20260915_merge_documentos_fiscais"
down_revision: Union[str, Sequence[str], None] = (
    "baseline_deepfarms_v1",
    "20260914_documentos_fiscais",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge-only revision; each parent applies its own schema changes."""


def downgrade() -> None:
    """Merge-only revision; downgrade restores both parent heads."""
