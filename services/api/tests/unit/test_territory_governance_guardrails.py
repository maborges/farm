"""Guardrails estáticos da arquitetura territorial oficial."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from agricola.production_units.models import ProductionUnit
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.models import AreaRural, FILHOS_PERMITIDOS, TipoArea
from core.models.unidade_produtiva import UnidadeProdutiva
from pecuaria.models.piquete import Piquete


REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_area_rural_permanece_arvore_territorial_oficial() -> None:
    columns = set(inspect(AreaRural).columns.keys())

    assert AreaRural.__tablename__ == "cadastros_areas_rurais"
    assert {"unidade_produtiva_id", "parent_id", "tipo", "nome"}.issubset(columns)
    assert FILHOS_PERMITIDOS[None] == {TipoArea.AREA_RURAL, TipoArea.INFRAESTRUTURA}


def test_talhao_e_piquete_permancem_tipos_de_area_rural() -> None:
    assert TipoArea.TALHAO in FILHOS_PERMITIDOS[TipoArea.GLEBA]
    assert FILHOS_PERMITIDOS[TipoArea.TALHAO] == {TipoArea.AREA_OPERACIONAL}
    assert TipoArea.PIQUETE in FILHOS_PERMITIDOS[TipoArea.AREA_OPERACIONAL]

    talhao_service_source = _read("services/api/agricola/services/talhao_service.py")
    assert 'tipo="TALHAO"' in talhao_service_source
    assert "AreaRural" in talhao_service_source


def test_area_operacional_permanece_tipo_e_nao_model_proprio() -> None:
    assert TipoArea.AREA_OPERACIONAL.value == "AREA_OPERACIONAL"

    tracked_files = {path.relative_to(REPO_ROOT).as_posix() for path in (REPO_ROOT / "services/api").rglob("*")}
    assert "services/api/core/models/area_operacional.py" not in tracked_files
    assert "services/api/core/cadastros/propriedades/area_operacional.py" not in tracked_files


def test_pec_piquetes_permanece_apenas_compatibilidade_legada() -> None:
    assert Piquete.__tablename__ == "pec_piquetes"

    model_source = _read("services/api/pecuaria/models/piquete.py")
    service_source = _read("services/api/pecuaria/services/piquete_service.py")
    expected_notice = "Compatibilidade legada. Não usar como fonte canônica em novos fluxos."

    assert expected_notice in model_source
    assert expected_notice in service_source
    assert "AreaRural.tipo = PIQUETE" in model_source
    assert "AreaRural.tipo = PIQUETE" in service_source


def test_propriedade_imovel_permanece_ponte_canonica() -> None:
    columns = set(inspect(PropriedadeImovel).columns.keys())

    assert PropriedadeImovel.__tablename__ == "propriedade_imovel"
    assert {"propriedade_id", "imovel_rural_id", "tipo_vinculo", "data_inicio"}.issubset(columns)


def test_production_unit_permanece_unidade_agricola_oficial() -> None:
    columns = set(inspect(ProductionUnit).columns.keys())
    source = _read("services/api/agricola/production_units/models.py")

    assert ProductionUnit.__tablename__ == "production_units"
    assert {"safra_id", "cultivo_id", "area_id"}.issubset(columns)
    assert "cadastros_areas_rurais.id" in source
    assert "safra + cultivo + área" in source


def test_unidade_produtiva_permanece_operacional_e_nao_fundiaria() -> None:
    columns = set(inspect(UnidadeProdutiva).columns.keys())
    source = _read("services/api/core/models/unidade_produtiva.py")
    expected_notice = "Compatibilidade legada. Não usar como fonte canônica em novos fluxos."

    assert {"codigo_car", "nirf", "ccir", "sigef_codigo", "numero_matricula"}.issubset(columns)
    assert expected_notice in source
    assert "Novos dados fundiários/documentais pertencem a ImovelRural." in source
    assert "Fazenda = UnidadeProdutiva" in source
