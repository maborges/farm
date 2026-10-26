"""Initial schema snapshot plus deterministic required global catalogs."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from clean_install import INSTALL_VERSION
from clean_install.catalog_validation import validate_catalog
from clean_install.manifest import (
    BASELINE_REVISION,
    SEED_CONTRACT_VERSION,
    verify_artifact_hashes,
)
from clean_install.seed_contract import apply_seeds

revision = INSTALL_VERSION
down_revision = None
branch_labels = ("deepfarms_clean_install",)
depends_on = None


def _apply_baseline_snapshot() -> None:
    api_root = Path(__file__).resolve().parents[3]
    path = api_root / "migrations" / "versions" / "20260908_baseline_deepfarms_v1.py"
    spec = importlib.util.spec_from_file_location("deepfarms_baseline_snapshot", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load approved baseline snapshot source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.revision != "baseline_deepfarms_v1" or module.down_revision is not None:
        raise RuntimeError("Baseline identity changed; clean install requires review")
    module.upgrade()


def upgrade() -> None:
    api_root = Path(__file__).resolve().parents[3]
    hashes = verify_artifact_hashes(api_root)
    _apply_baseline_snapshot()
    apply_seeds(op.get_bind())
    op.create_table(
        "deepfarms_install_manifest",
        sa.Column("singleton", sa.Boolean(), primary_key=True, nullable=False),
        sa.Column("install_version", sa.String(length=64), nullable=False),
        sa.Column("baseline_revision", sa.String(length=64), nullable=False),
        sa.Column("baseline_sha256", sa.String(length=64), nullable=False),
        sa.Column("seed_contract_version", sa.String(length=64), nullable=False),
        sa.Column("seed_contract_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "installed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("singleton IS TRUE", name="ck_deepfarms_install_manifest_singleton"),
        schema="farms",
    )
    op.get_bind().execute(
        sa.text("""
            INSERT INTO farms.deepfarms_install_manifest
                (singleton, install_version, baseline_revision, baseline_sha256,
                 seed_contract_version, seed_contract_sha256)
            VALUES (true, :install_version, :baseline_revision, :baseline_sha256,
                    :seed_contract_version, :seed_contract_sha256)
        """),
        {
            "install_version": INSTALL_VERSION,
            "baseline_revision": BASELINE_REVISION,
            "baseline_sha256": hashes["baseline_sha256"],
            "seed_contract_version": SEED_CONTRACT_VERSION,
            "seed_contract_sha256": hashes["seed_contract_sha256"],
        },
    )
    validate_catalog(op.get_bind(), expected_manifest=hashes, check_version=False)


def downgrade() -> None:
    raise RuntimeError("Clean-install snapshot is irreversible; discard the new database")
