from pathlib import Path

from core.model_registry import (
    BASELINE_DECISIONS,
    BASELINE_EXCLUDED_TABLES,
    LEGACY_BALANCA_TABLES,
    baseline_candidate_tables,
)


def test_baseline_orm_scope_is_deterministic() -> None:
    baseline = baseline_candidate_tables()

    assert len(baseline) == 344
    assert not baseline.intersection(BASELINE_EXCLUDED_TABLES)
    assert len(BASELINE_DECISIONS) == 34


def test_legacy_balanca_tables_are_outside_baseline_and_schema_is_farms() -> None:
    baseline = baseline_candidate_tables()
    env_source = Path(__file__).parents[3].joinpath("migrations/env.py").read_text()

    assert not baseline.intersection(LEGACY_BALANCA_TABLES)
    assert "SET search_path TO farms" in env_source
