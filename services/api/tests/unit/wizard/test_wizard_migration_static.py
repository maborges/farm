from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "migrations"
    / "versions"
    / "20260630_wizard_foundation.py"
)


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "wizard_foundation_migration", MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wizard_migration_static_contracts() -> None:
    module = _load_migration_module()
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert module.revision == "20260630_wizard_foundation"
    assert module.down_revision == "c8be30cbd1fe"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    for table_name in (
        "wizard_implantacoes_operacionais",
        "wizard_implantacoes_etapas",
        "wizard_implantacoes_checklist_itens",
        "wizard_implantacoes_pendencias",
        "wizard_implantacoes_historico",
    ):
        assert f'"{table_name}"' in source or f"'{table_name}'" in source

    assert "uq_wizard_implantacao_ativa_por_tenant" in source
    assert "uq_wizard_etapa_implantacao_codigo" in source
    assert "uq_wizard_checklist_implantacao_codigo" in source
    assert "ck_wizard_implantacao_status_requires_unidade" in source
    assert "ck_wizard_implantacao_blocked_requires_blocked_at" in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source


def test_wizard_migration_child_rls_and_append_only_history() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "_enable_child_rls" in source
    assert "EXISTS (" in source
    assert "append_only=True" in source
    assert "wizard_implantacoes_historico" in source
    assert "CREATE POLICY" in source
    assert "DROP POLICY IF EXISTS" in source
