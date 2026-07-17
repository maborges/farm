"""Guardrails dos resíduos de fronteira territorial tratados na fase 03B."""

from pathlib import Path

from sqlalchemy import inspect

from core.cadastros.propriedades import models, schemas
from core.cadastros.propriedades.models import AreaRural
from core.cadastros.propriedades.propriedade_schemas import PropriedadeCreate, PropriedadeUpdate
from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate, UnidadeProdutivaUpdate
from pecuaria.schemas.piquete_schema import PiqueteCreate

REPO_ROOT = Path(__file__).resolve().parents[4]
ANALISES_DIR = (
    REPO_ROOT
    / "apps/web/src/app/(dashboard)/dashboard/agricola/analises-solo/components"
)
FUNDIARIO_FIELDS = {
    "nirf",
    "cib",
    "ccir",
    "car_numero",
    "codigo_car",
    "sigef_codigo",
    "numero_matricula",
    "cartorio_id",
    "itr_numero",
}
ANALISES_COMPONENTS = (
    ANALISES_DIR / "analises-client.tsx",
    ANALISES_DIR / "nova-analise-modal.tsx",
)


def test_schemas_operacionais_nao_aceitam_documentos_fundiarios() -> None:
    schemas_operacionais = (
        UnidadeProdutivaCreate,
        UnidadeProdutivaUpdate,
        PropriedadeCreate,
        PropriedadeUpdate,
        schemas.AreaRuralCreate,
        schemas.AreaRuralUpdate,
        PiqueteCreate,
    )

    for schema in schemas_operacionais:
        assert FUNDIARIO_FIELDS.isdisjoint(schema.model_fields), schema.__name__


def test_via_fundiaria_legada_de_area_rural_foi_removida() -> None:
    assert not hasattr(schemas, "MatriculaCreate")
    assert not hasattr(schemas, "MatriculaUpdate")
    assert not hasattr(models, "MatriculaImovel")
    assert "matriculas" not in inspect(AreaRural).relationships

    router_source = (
        REPO_ROOT / "services/api/core/cadastros/propriedades/router.py"
    ).read_text(encoding="utf-8")
    assert '/{area_id}/matriculas' not in router_source


def test_migration_remove_tabela_legada_com_downgrade() -> None:
    migration = (
        REPO_ROOT
        / "services/api/migrations/versions/20260717_remove_area_matriculas_legacy.py"
    )
    source = migration.read_text(encoding="utf-8")

    assert "op.drop_table(TABLE_NAME)" in source
    assert 'op.create_table(' in source
    assert '"cadastros_areas_matriculas"' in source


def test_analises_solo_resolvem_nome_por_unidade_produtiva() -> None:
    for component in ANALISES_COMPONENTS:
        source = component.read_text(encoding="utf-8")
        assert '"/unidades-produtivas/"' in source
        assert "propriedades.find" not in source
        assert 'apiFetch<Propriedade[]>("/cadastros/propriedades")' not in source
        assert "as unknown as" not in source


def test_nao_existe_sincronismo_inverso_imovel_para_unidade() -> None:
    cadastro_source = (
        REPO_ROOT / "services/api/core/services/cadastro_completo_service.py"
    ).read_text(encoding="utf-8")
    imovel_source = (
        REPO_ROOT / "services/api/imoveis/services/imovel_service.py"
    ).read_text(encoding="utf-8")

    assert "_sincronizar_imovel_principal_com_unidade" in cadastro_source
    assert "_sincronizar_unidade" not in imovel_source
    assert "UnidadeProdutivaService" not in imovel_source
