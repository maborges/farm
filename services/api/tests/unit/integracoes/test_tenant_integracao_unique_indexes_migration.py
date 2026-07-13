from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "migrations"
    / "versions"
    / "20260712_integrations_tenant_integracao_unique_indexes.py"
)


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "tenant_integracao_unique_indexes_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_static_contracts() -> None:
    module = _load_migration_module()
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert module.revision == "20260712_integrations_tenant_integracao_unique_indexes"
    assert module.down_revision == "f1dfe22c7fa5"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    assert "uq_tenant_integracoes_provider_scope_tenant" in source
    assert "uq_tenant_integracoes_provider_scope_estabelecimento" in source
    assert "scope_type = 'TENANT'" in source
    assert "scope_type = 'ESTABELECIMENTO'" in source
    assert "deleted_at IS NULL" in source
    assert "CREATE UNIQUE INDEX CONCURRENTLY" in source
    assert "autocommit_block" in source


def test_upgrade_cria_indices_na_ordem_certa(monkeypatch) -> None:
    module = _load_migration_module()
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(module, "_abort_if_blockers_found", lambda: None)
    monkeypatch.setattr(
        module,
        "_create_index_concurrently",
        lambda name, ddl: calls.append((name, ddl)),
    )

    module.upgrade()

    assert calls[0][0] == "uq_tenant_integracoes_provider_scope_tenant"
    assert calls[1][0] == "uq_tenant_integracoes_provider_scope_estabelecimento"
    assert "scope_type = 'TENANT'" in calls[0][1]
    assert "scope_type = 'ESTABELECIMENTO'" in calls[1][1]


def test_downgrade_remove_somente_indices_novos(monkeypatch) -> None:
    module = _load_migration_module()
    calls: list[str] = []

    monkeypatch.setattr(
        module,
        "_drop_index_concurrently",
        lambda name: calls.append(name),
    )

    module.downgrade()

    assert calls == [
        "uq_tenant_integracoes_provider_scope_estabelecimento",
        "uq_tenant_integracoes_provider_scope_tenant",
    ]
