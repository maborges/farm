"""Testes unitarios de governanca documental territorial/fundiaria."""

from __future__ import annotations

from sqlalchemy import inspect

from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.models import AreaRural, RegistroAmbiental
from core.cadastros.propriedades.propriedade_models import DocumentoExploracao, ExploracaoRural, Propriedade
from core.models.unidade_produtiva import UnidadeProdutiva
from imoveis.models.imovel import (
    AvaliacaoImovel,
    Cartorio,
    ContratoArrendamento,
    DocumentoLegal,
    ImovelRural,
    MatriculaImovelRural,
)


def test_propriedades_mantem_fronteira_operacional_sem_documentacao_legal_duplicada() -> None:
    propriedade_columns = set(inspect(Propriedade).columns.keys())
    propriedade_relationships = set(inspect(Propriedade).relationships.keys())
    unidade_columns = set(inspect(UnidadeProdutiva).columns.keys())

    assert "propriedade_imoveis" in propriedade_relationships
    assert "exploracoes" in propriedade_relationships

    assert "car_numero" not in propriedade_columns
    assert "ccir_numero" not in propriedade_columns
    assert "nirf" not in propriedade_columns
    assert "numero_matricula" not in propriedade_columns
    assert "cartorio_id" not in propriedade_columns
    assert "documentos" not in propriedade_relationships

    assert {"codigo_car", "nirf", "ccir", "sigef_codigo", "numero_matricula"}.isdisjoint(unidade_columns)
    assert {"area_app_ha", "area_rl_ha"}.issubset(unidade_columns)


def test_imoveis_rurais_concentram_lastro_fundiario_e_documental() -> None:
    imovel_columns = set(inspect(ImovelRural).columns.keys())
    imovel_relationships = set(inspect(ImovelRural).relationships.keys())

    assert {"nirf", "car_numero", "ccir_numero", "numero_matricula", "cartorio_id"}.issubset(imovel_columns)
    assert {"area_app_ha", "area_rl_ha"}.issubset(imovel_columns)
    assert {"documentos", "contratos_arrendamento", "avaliacoes", "propriedade_imoveis"}.issubset(
        imovel_relationships
    )

    assert DocumentoLegal.__tablename__ == "imoveis_documentos"
    assert Cartorio.__tablename__ == "imoveis_cartorios"
    assert MatriculaImovelRural.__tablename__ == "imoveis_matriculas"
    assert ContratoArrendamento.__tablename__ == "imoveis_arrendamentos"
    assert AvaliacaoImovel.__tablename__ == "imoveis_avaliacoes"


def test_propriedade_imovel_e_apenas_a_ponte_canonica() -> None:
    vinculo_columns = set(inspect(PropriedadeImovel).columns.keys())

    assert PropriedadeImovel.__tablename__ == "propriedade_imovel"
    assert {"tenant_id", "propriedade_id", "imovel_rural_id", "tipo_vinculo", "origem_documental"}.issubset(
        vinculo_columns
    )
    assert "path_storage" not in vinculo_columns
    assert "numero_matricula" not in vinculo_columns
    assert "car_numero" not in vinculo_columns
    assert "ccir_numero" not in vinculo_columns
    assert "nirf" not in vinculo_columns
    assert "valor_total" not in vinculo_columns


def test_evidencias_operacionais_ficam_em_suporte_territorial() -> None:
    area_relationships = set(inspect(AreaRural).relationships.keys())

    assert {"registros_ambientais", "valores_patrimoniais", "arquivos_geo"}.issubset(
        area_relationships
    )
    assert "matriculas" not in area_relationships
    assert RegistroAmbiental.__tablename__ == "cadastros_areas_registros_ambientais"
    assert DocumentoExploracao.__tablename__ == "cadastros_documentos_exploracao"
    assert ExploracaoRural.__tablename__ == "cadastros_exploracoes_rurais"
