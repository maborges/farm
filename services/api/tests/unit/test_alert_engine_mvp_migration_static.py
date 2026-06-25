from __future__ import annotations

import importlib.util
from pathlib import Path


MIGRATION_PATH = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "20260625_alert_engine_mvp.py"


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("alert_engine_mvp_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_alert_engine_mvp_migration_static_contracts() -> None:
    module = _load_migration_module()
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert module.revision == "20260625_alert_engine_mvp"
    assert module.down_revision == "20260624_pecuaria_vacinacao_categoria_cost_allocations"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    for table_name in (
        "alert_events",
        "alert_indicators",
        "operational_alerts",
        "alert_insights",
        "alert_lifecycle_events",
    ):
        assert f'"{table_name}"' in source or f"'{table_name}'" in source

    assert "alert_deliveries" not in source
    assert "uq_operational_alerts_active_dedupe" in source
    assert "ck_operational_alerts_status" in source
    assert "ck_alert_indicators_single_value" in source
