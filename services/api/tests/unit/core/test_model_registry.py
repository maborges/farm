import ast
from pathlib import Path

from core.database import Base
from core.model_registry import (
    BASELINE_DECISIONS,
    BASELINE_EXCLUDED_TABLES,
    LEGACY_BALANCA_TABLES,
    MODEL_MODULES,
    baseline_candidate_tables,
    register_models,
    table_owners,
)


def _discovered_table_names() -> set[str]:
    names: set[str] = set()
    api_root = Path(__file__).parents[3]
    excluded = {".venv", "migrations", "tests", "__pycache__"}
    for path in api_root.rglob("*.py"):
        if excluded.intersection(path.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            has_table_name = any(
                isinstance(target, ast.Name) and target.id == "__tablename__"
                for target in node.targets
            )
            if not has_table_name:
                continue
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                names.add(node.value.value)
    return names


def test_registry_is_idempotent_and_reproducible() -> None:
    register_models()
    first = set(Base.metadata.tables)
    register_models()
    second = set(Base.metadata.tables)

    assert first == second
    assert len(MODEL_MODULES) > 0
    assert len(first) == 373
    assert len(baseline_candidate_tables()) == 344
    assert len(BASELINE_DECISIONS) == 34
    assert not (set(baseline_candidate_tables()) & set(LEGACY_BALANCA_TABLES))


def test_registry_covers_every_production_model_table() -> None:
    register_models()

    assert _discovered_table_names() <= set(Base.metadata.tables)


def test_every_model_has_a_final_baseline_decision() -> None:
    register_models()

    discovered = _discovered_table_names()
    decided = discovered - set(BASELINE_DECISIONS)
    assert decided | set(BASELINE_DECISIONS) == discovered
    assert not (set(BASELINE_EXCLUDED_TABLES) - discovered)


def test_registry_has_no_incompatible_table_collisions() -> None:
    register_models()

    collisions = {name: owners for name, owners in table_owners().items() if len(owners) > 1}
    assert collisions == {}
