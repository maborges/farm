"""Guardrails de anticorrupcao para legados territoriais/fundiarios."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.models import AreaRural
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade
from core.models.unidade_produtiva import UnidadeProdutiva
from imoveis.models.imovel import DocumentoLegal, ImovelRural


REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _assert_no_tokens(source: str, forbidden_tokens: tuple[str, ...]) -> None:
    violacoes = [token for token in forbidden_tokens if token in source]
    assert not violacoes, f"Tokens proibidos encontrados: {', '.join(violacoes)}"


def test_unidade_produtiva_permanece_compatibilidade_historica() -> None:
    columns = set(inspect(UnidadeProdutiva).columns.keys())
    relationships = set(inspect(UnidadeProdutiva).relationships.keys())

    assert {"codigo_car", "nirf", "ccir", "sigef_codigo"}.issubset(columns)
    assert "documentos" not in relationships
    assert "propriedade_imoveis" not in relationships


def test_escrita_oficial_operacional_nao_captura_campos_fundiarios_legados() -> None:
    source = _read("services/api/core/cadastros/propriedades/propriedade_service.py")
    _assert_no_tokens(
        source,
        (
            "codigo_car",
            "car_numero",
            "ccir_numero",
            "nirf =",
            "ccir =",
            "sigef_codigo",
            "numero_matricula",
            "cartorio_id",
        ),
    )


def test_escrita_oficial_fundiaria_nao_captura_campos_operacionais() -> None:
    source = _read("services/api/imoveis/services/imovel_service.py")
    _assert_no_tokens(
        source,
        (
            "AreaRural",
            "ExploracaoRural",
            "DocumentoExploracao",
            "RegistroAmbiental",
        ),
    )


def test_ponte_canonica_nao_se_torna_repositorio_documental() -> None:
    columns = set(inspect(PropriedadeImovel).columns.keys())

    assert "path_storage" not in columns
    assert "numero_matricula" not in columns
    assert "car_numero" not in columns
    assert "ccir_numero" not in columns
    assert "nirf" not in columns
    assert "valor_total" not in columns


def test_documentacao_formaliza_compatibilidade_e_fonte_oficial() -> None:
    doc = _read("docs/architecture/territorial-legacy-anticorruption-rules.md")
    assert "Compatibilidade historica" in doc
    assert "Fonte oficial operacional" in doc
    assert "Fonte oficial fundiaria" in doc
    assert "PropriedadeImovel" in doc
    assert "unidades_produtivas.codigo_car" in doc


def test_area_rural_mantem_fronteira_operacional_e_de_suporte() -> None:
    columns = set(inspect(AreaRural).columns.keys())
    relationships = set(inspect(AreaRural).relationships.keys())

    assert "car_numero" not in columns
    assert "nirf" not in columns
    assert "ccir_numero" not in columns
    assert "numero_matricula" not in columns
    assert {"matriculas", "registros_ambientais", "valores_patrimoniais", "arquivos_geo"}.issubset(
        relationships
    )
    assert "propriedade_imoveis" not in relationships
