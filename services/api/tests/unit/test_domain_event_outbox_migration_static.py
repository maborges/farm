from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "20260626_domain_event_outbox.py"
)


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("domain_event_outbox_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_domain_event_outbox_migration_static_contracts() -> None:
    module = _load_migration_module()
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert module.revision == "20260626_domain_event_outbox"
    assert module.down_revision == "20260625_alert_engine_mvp"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    for table_name in ("domain_event_outbox",):
        assert table_name in source

    assert "uq_domain_event_outbox_tenant_idempotency_key" in source
    assert "ix_domain_event_outbox_status_next_attempt_at" in source
    assert "ENABLE ROW LEVEL SECURITY" in source
