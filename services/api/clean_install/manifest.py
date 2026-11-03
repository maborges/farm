"""Immutable source identity for clean-install revision v1."""

from __future__ import annotations

from pathlib import Path

from clean_install import INSTALL_VERSION

BASELINE_REVISION = "baseline_deepfarms_v1"
SEED_CONTRACT_VERSION = "global_catalogs_v1"
# Filled from the reviewed source files and asserted before any snapshot DDL.
BASELINE_SHA256 = "b32da6be0f5f089c9d75fc2c0da4784e8dccaeb6303be5c03dbc6156c8275fbc"
SEED_CONTRACT_SHA256 = "92e09a8584142e0da7ebac3e5b13cbcc1663105a895d47dba1927d09d8c6cea8"


def artifact_hashes(api_root: Path) -> dict[str, str]:
    import hashlib

    baseline = api_root / "migrations/versions/20260908_baseline_deepfarms_v1.py"
    seed_sources = (
        api_root / "clean_install/seed_contract.py",
        api_root / "scripts/initial_load/seed_unidades_medida.py",
        api_root / "scripts/initial_load/seed_categorias_produto.py",
        api_root / "scripts/initial_load/seed_fases_operacao.py",
        api_root / "scripts/initial_load/seed_tipos_servico.py",
        api_root / "scripts/initial_load/seed_tipos_relacionamento.py",
    )
    seed_digest = hashlib.sha256()
    for source in seed_sources:
        seed_digest.update(source.relative_to(api_root).as_posix().encode())
        seed_digest.update(b"\0")
        seed_digest.update(source.read_bytes())
    return {
        "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
        "seed_contract_sha256": seed_digest.hexdigest(),
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
