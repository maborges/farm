from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "migrations"
    / "versions"
    / "20260924_material_requisition_01c.py"
)


def test_foundation_migration_is_incremental_and_reversible() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260924_material_requisition_01c"' in source
    assert (
        'down_revision: str | Sequence[str] | None = "20260915_merge_documentos_fiscais"'
        in source
    )
    assert "def upgrade" in source
    assert "def downgrade" in source
    assert "estoque_requisicao_item_eventos" in source
    assert "estoque_requisicao_responsabilidades" in source
    assert "uq_req_item_evento_tenant_client_operation" in source
    assert "fn_estoque_requisicao_item_evento_append_only" in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "LEGACY_DELIVERED" in source
    assert "UPDATE estoque_requisicoes_itens" not in source


def test_foundation_migration_backfill_only_copies_structural_tenant_and_classifies_legacy() -> (
    None
):
    source = MIGRATION.read_text(encoding="utf-8")

    assert "UPDATE farms.estoque_requisicoes_itens" in source
    assert "UPDATE farms.estoque_requisicoes" in source
    assert "quantidade_consumida" not in source
    assert "cost_allocations" not in source
    assert "dre" not in source.lower()
