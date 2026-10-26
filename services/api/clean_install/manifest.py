"""Immutable source identity for clean-install revision v1."""

from __future__ import annotations

from pathlib import Path

BASELINE_REVISION = "baseline_deepfarms_v1"
SEED_CONTRACT_VERSION = "global_catalogs_v1"
# Filled from the reviewed source files and asserted before any snapshot DDL.
BASELINE_SHA256 = "b32da6be0f5f089c9d75fc2c0da4784e8dccaeb6303be5c03dbc6156c8275fbc"
SEED_CONTRACT_SHA256 = "1e6a717dc70effdc9cbc65407bbf4126ed2f59b36f2a6b0c7f8d37a61507b4fe"


def artifact_hashes(api_root: Path) -> dict[str, str]:
    import hashlib

    baseline = api_root / "migrations/versions/20260908_baseline_deepfarms_v1.py"
    seeds = api_root / "clean_install/seed_contract.py"
    return {
        "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
        "seed_contract_sha256": hashlib.sha256(seeds.read_bytes()).hexdigest(),
    }


def verify_artifact_hashes(api_root: Path) -> dict[str, str]:
    observed = artifact_hashes(api_root)
    if observed != {
        "baseline_sha256": BASELINE_SHA256,
        "seed_contract_sha256": SEED_CONTRACT_SHA256,
    }:
        raise RuntimeError(
            "Pinned baseline/seed artifact hash changed; clean install revision v1 is stale"
        )
    return observed
