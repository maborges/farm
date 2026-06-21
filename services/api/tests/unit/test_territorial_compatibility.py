"""Regressões de compatibilidade entre Propriedades, Imóveis Rurais e o vínculo canônico."""

from sqlalchemy import inspect

from core.cadastros.propriedade_imovel.models import PropriedadeImovel, TipoVinculoPropriedadeImovel
from core.cadastros.propriedades.propriedade_models import Propriedade
from imoveis.models.imovel import ImovelRural


def test_propriedade_mantem_fronteira_operacional():
    attrs = set(inspect(Propriedade).attrs.keys())

    assert "propriedade_imoveis" in attrs
    assert "exploracoes" in attrs
    assert {"car_numero", "nirf", "ccir_numero", "numero_matricula", "cartorio_id"}.isdisjoint(attrs)


def test_imovel_mantem_fronteira_fundiaria():
    attrs = set(inspect(ImovelRural).attrs.keys())

    assert {"nirf", "car_numero", "ccir_numero", "numero_matricula", "cartorio_id"}.issubset(attrs)
    assert "propriedade_imoveis" in attrs
    assert {"talhoes", "safras", "producoes"}.isdisjoint(attrs)


def test_propriedade_imovel_e_unica_ponte_canonica():
    attrs = set(inspect(PropriedadeImovel).attrs.keys())
    colunas = set(inspect(PropriedadeImovel).columns.keys())

    assert PropriedadeImovel.__tablename__ == "propriedade_imovel"
    assert TipoVinculoPropriedadeImovel.ARRENDAMENTO.value == "ARRENDAMENTO"
    assert {"tenant_id", "propriedade_id", "imovel_rural_id", "tipo_vinculo", "data_inicio"}.issubset(colunas)
    assert {"car_numero", "nirf", "ccir_numero", "numero_matricula", "area_total_ha"}.isdisjoint(attrs)

