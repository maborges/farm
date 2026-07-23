"""Guardrails estáticos da arquitetura de produtos, culturas e commodities."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from agricola.cadastros.models import Cultura
from agricola.colheita.models import ProdutoColhido
from core.cadastros.commodities.models import Commodity
from core.cadastros.produtos.models import Produto, ProdutoAgricola, ProdutoCultura, ProdutoEPI, ProdutoEstoque
from operacional.models.compras import ItemPedidoCompra, SolicitacaoCompra
from operacional.models.estoque import EstoqueMovimento, LoteEstoque, SaldoEstoque
from pecuaria.models.manejo import ManejoLote


REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_produto_permanece_catalogo_mestre_operacional() -> None:
    columns = set(inspect(Produto).columns.keys())
    source = _read("services/api/core/cadastros/produtos/models.py")

    assert Produto.__tablename__ == "cadastros_produtos"
    assert {"nome", "tipo", "unidade_medida", "estoque_minimo", "preco_medio"}.issubset(columns)
    assert "NÃO representa produtos colhidos / commodities" in source


def test_extensoes_de_produto_permanecem_no_mesmo_aggregate() -> None:
    assert ProdutoAgricola.__tablename__ == "cadastros_produtos_agricola"
    assert ProdutoEstoque.__tablename__ == "cadastros_produtos_estoque"
    assert ProdutoEPI.__tablename__ == "cadastros_produtos_epi"

    for model in (ProdutoAgricola, ProdutoEstoque, ProdutoEPI):
        columns = inspect(model).columns
        assert columns["produto_id"].foreign_keys
        assert next(iter(columns["produto_id"].foreign_keys)).target_fullname == "cadastros_produtos.id"


def test_cultura_canonica_permanece_em_produto_cultura() -> None:
    columns = set(inspect(ProdutoCultura).columns.keys())
    source = _read("services/api/agricola/cadastros/models.py")

    assert ProdutoCultura.__tablename__ == "cadastros_culturas"
    assert {"nome", "ativa"}.issubset(columns)
    assert Cultura.__tablename__ == "culturas"
    assert "Compatibilidade legada. Não usar como fonte canônica em novos fluxos." in source
    assert "ProdutoCultura / cadastros_culturas" in source


def test_commercializacao_e_hedge_permanecem_baseados_em_commodity() -> None:
    commodity_columns = set(inspect(Commodity).columns.keys())
    comercializacao_source = _read("services/api/financeiro/comercializacao/models.py")
    hedge_source = _read("services/api/financeiro/hedge/models.py")

    assert Commodity.__tablename__ == "cadastros_commodities"
    assert {"nome", "codigo", "tipo", "unidade_padrao"}.issubset(commodity_columns)
    assert "ForeignKey(\"cadastros_commodities.id\"" in comercializacao_source
    assert "ForeignKey(\"cadastros_commodities.id\"" in hedge_source
    assert "O vínculo canônico de mercado permanece em commodity_id." in hedge_source


def test_produto_colhido_permanece_camada_distinta_de_produto() -> None:
    columns = inspect(ProdutoColhido).columns
    source = _read("services/api/agricola/colheita/models.py")

    assert ProdutoColhido.__tablename__ == "agricola_produtos_colhidos"
    assert next(iter(columns["commodity_id"].foreign_keys)).target_fullname == "cadastros_commodities.id"
    assert "produto_id" not in columns.keys()
    assert "Não usar Produto como substituto desta camada em novos fluxos agrícolas." in source


def test_compras_estoque_e_pecuaria_usam_produto_sem_cadastro_paralelo() -> None:
    expected_target = "cadastros_produtos.id"

    for model, field in (
        (ItemPedidoCompra, "produto_id"),
        (SolicitacaoCompra, "produto_id"),
        (SaldoEstoque, "produto_id"),
        (LoteEstoque, "produto_id"),
        (EstoqueMovimento, "produto_id"),
        (ManejoLote, "produto_id"),
    ):
        column = inspect(model).columns[field]
        assert next(iter(column.foreign_keys)).target_fullname == expected_target


def test_aliases_e_campos_textuais_permanecem_somente_como_compatibilidade() -> None:
    alias_source = _read("services/api/core/cadastros/models.py")
    safra_source = _read("services/api/agricola/safras/models.py")
    cultivo_source = _read("services/api/agricola/cultivos/models.py")

    assert "ProdutoCatalogo permanece apenas como alias histórico de Produto." in alias_source
    assert "A cultura canônica deve ser resolvida via Cultivo.cultivar_id -> ProdutoCultura." in safra_source
    assert "A cultura canônica do cultivo deve ser resolvida por cultivar_id -> ProdutoCultura." in cultivo_source
