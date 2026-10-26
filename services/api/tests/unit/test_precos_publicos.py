"""
Testes unitários e de integração para os preços agropecuários públicos reais (DERAL/SEAB-PR).
Garante:
1. Retorno de status 200 com contrato PrecosPublicosResponse completo
2. Presença dos 7 preços originais B4 intactos e adição dos 14 novos produtos P1 (total 21 itens)
3. Endpoint GET /api/v1/public/mercado/catalogo com 22 commodities e variantes comerciais
4. Segregação rigorosa de urlConsultaInstitucional e urlDocumentoDownload
5. Semântica precisa: tipoPreco = PRECO_MEDIO_RECEBIDO_PRODUTOR
6. Consulta individual por commodity com 404 seguro para itens sem preço oficial aberto (ex: algodão)
7. Rota pública e anônima sem exigência de JWT nem conexão ao PostgreSQL comercial
"""

from __future__ import annotations

import sys
from pathlib import Path

# Adiciona services/api ao sys.path para execucao direta ou via runner
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from public_mercado.precos_publicos import (
    PRECOS_OFICIAIS_HOMOLOGADOS,
    carregar_catalogo_mercado,
    carregar_precos_publicos,
)
from public_mercado.router import router as public_mercado_router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(public_mercado_router, prefix="/api/v1")
    return TestClient(app)


def test_carregar_precos_publicos_contrato():
    """Valida que todos os 21 itens homologados respeitam o schema do Pydantic."""
    itens = carregar_precos_publicos()
    assert len(itens) == 21
    ids = {item.id for item in itens}

    # 7 itens originais da B4
    assert "soja" in ids
    assert "milho" in ids
    assert "cafe-arabica" in ids
    assert "boi-gordo" in ids
    assert "trigo" in ids
    assert "arroz" in ids
    assert "feijao" in ids

    # 14 novos itens P1 do DERAL
    assert "amendoim" in ids
    assert "feijao-preto" in ids
    assert "aveia-branca" in ids
    assert "canola" in ids
    assert "cevada" in ids
    assert "cana-de-acucar" in ids
    assert "erva-mate" in ids
    assert "mandioca-industrial" in ids
    assert "boi-magro" in ids
    assert "frango-vivo" in ids
    assert "leite" in ids
    assert "ovo-grande" in ids
    assert "suino" in ids
    assert "vaca-em-pe" in ids

    for item in itens:
        assert item.valor > 0
        assert item.moeda == "BRL"
        assert item.unidade != ""
        assert item.pracaReferencia != ""
        assert item.siglaFonte == "DERAL/SEAB-PR"
        assert item.tipoPreco == "PRECO_MEDIO_RECEBIDO_PRODUTOR"
        assert item.periodicidade == "SEMANAL"
        assert item.dataReferencia == "2026-10-16"
        assert item.documentoOficial.endswith("/Precos/prp.xls")
        assert item.documentoHashSha256 == "65582dc4c47c8993415dc71ee9af6ed69651b7279d65ab31f4316a1bc787dde1"
        assert item.registroOriginal.startswith("Rav!X")
        assert item.valorOriginal > 0
        assert item.transformacaoAplicada == "Arredondamento decimal HALF_UP para 2 casas"
        assert item.urlConsultaInstitucional.startswith("https://")
        assert item.urlDocumentoDownload is not None


def test_endpoint_precos_publicos_sucesso(client: TestClient):
    """Garante que GET /api/v1/public/mercado/precos responde 200 com 21 itens."""
    response = client.get("/api/v1/public/mercado/precos")
    assert response.status_code == 200
    payload = response.json()

    assert payload["sucesso"] is True
    assert payload["versao"] == "1.0"
    assert payload["estadoDisponibilidade"] == "NORMAL"
    assert "avisoLegal" in payload
    assert isinstance(payload["itens"], list)
    assert len(payload["itens"]) == len(PRECOS_OFICIAIS_HOMOLOGADOS)

    # Valida presença dos 7 preços preservados da B4
    soja = next(i for i in payload["itens"] if i["id"] == "soja")
    assert soja["valor"] == 134.98
    assert soja["unidade"] == "Saca de 60 kg"

    milho = next(i for i in payload["itens"] if i["id"] == "milho")
    assert milho["valor"] == 51.77

    cafe = next(i for i in payload["itens"] if i["id"] == "cafe-arabica")
    assert cafe["valor"] == 1380.51
    assert cafe["commodityNome"] == "Café Beneficiado (Produtor)"
    assert cafe["registroOriginal"] == "Rav!X7"

    feijao = next(i for i in payload["itens"] if i["id"] == "feijao")
    assert feijao["commodityNome"] == "Feijão de Cor"

    boi = next(i for i in payload["itens"] if i["id"] == "boi-gordo")
    assert boi["valor"] == 371.21

    # Valida novas adições P1
    leite = next(i for i in payload["itens"] if i["id"] == "leite")
    assert leite["valor"] == 2.81
    assert leite["commodityNome"] == "Leite (Produtor)"
    assert leite["unidade"] == "Litro"

    cevada = next(i for i in payload["itens"] if i["id"] == "cevada")
    assert cevada["commodityNome"] == "Cevada em Grão"

    frango = next(i for i in payload["itens"] if i["id"] == "frango-vivo")
    assert frango["valor"] == 4.95
    assert frango["unidade"] == "Quilo (kg)"


def test_endpoint_catalogo_dinamico_sucesso(client: TestClient):
    """Garante que GET /api/v1/public/mercado/catalogo retorna 22 commodities estruturadas."""
    response = client.get("/api/v1/public/mercado/catalogo")
    assert response.status_code == 200
    payload = response.json()

    assert payload["sucesso"] is True
    assert payload["totalItens"] == 22
    assert len(payload["itens"]) == 22

    categorias_validas = {
        "GRAOS_CEREAIS",
        "CAFE",
        "PECUARIA",
        "LEGUMINOSAS",
        "FIBRAS",
        "HORTIFRUTI",
        "CANA_DERIVADOS",
        "OUTROS",
    }

    ids = {item["id"] for item in payload["itens"]}
    assert "soja" in ids
    assert "algodao" in ids
    assert "leite" in ids
    assert "cana-de-acucar" in ids

    for item in payload["itens"]:
        assert item["categoria"] in categorias_validas
        assert len(item["classificacaoAgronomica"]) > 0
        assert len(item["descricao"]) > 0
        assert item["urlConsultaInstitucional"].startswith("https://")
        assert isinstance(item["variantes"], list)
        assert len(item["variantes"]) >= 1

    # Valida item com preço real DERAL
    soja_item = next(i for i in payload["itens"] if i["id"] == "soja")
    assert soja_item["valor"] == 134.98
    assert soja_item["estadoDisponibilidade"] == "DISPONIVEL"
    assert soja_item["urlDocumentoDownload"] is not None
    assert soja_item["variantes"][0]["varianteId"] == "deral-pr-soja"

    # Valida item cadastral sem cotação aberta DERAL (Algodão)
    algodao_item = next(i for i in payload["itens"] if i["id"] == "algodao")
    assert algodao_item["valor"] is None
    assert algodao_item["estadoDisponibilidade"] == "LINK_HOMOLOGADO"
    assert algodao_item["urlDocumentoDownload"] is None
    assert algodao_item["variantes"][0]["varianteId"] == "conab-nacional-algodao"


def test_endpoint_preco_por_commodity_existente(client: TestClient):
    """Garante que GET /api/v1/public/mercado/precos/{id} retorna os dados da commodity."""
    response = client.get("/api/v1/public/mercado/precos/milho")
    assert response.status_code == 200
    item = response.json()
    assert item["id"] == "milho"
    assert item["valor"] == 51.77
    assert item["unidade"] == "Saca de 60 kg"
    assert item["siglaFonte"] == "DERAL/SEAB-PR"


def test_endpoint_preco_por_commodity_inexistente(client: TestClient):
    """Garante que GET /api/v1/public/mercado/precos/{id} retorna 404 para produtos sem preço DERAL."""
    response = client.get("/api/v1/public/mercado/precos/algodao")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "não homologada" in data["detail"]

    response_inv = client.get("/api/v1/public/mercado/precos/inexistente_xyz")
    assert response_inv.status_code == 404


if __name__ == "__main__":
    print("Iniciando testes unitários de preços públicos e catálogo...")
    test_carregar_precos_publicos_contrato()
    print("✔ test_carregar_precos_publicos_contrato passou.")
    app = FastAPI()
    app.include_router(public_mercado_router, prefix="/api/v1")
    c = TestClient(app)
    test_endpoint_precos_publicos_sucesso(c)
    print("✔ test_endpoint_precos_publicos_sucesso passou.")
    test_endpoint_catalogo_dinamico_sucesso(c)
    print("✔ test_endpoint_catalogo_dinamico_sucesso passou.")
    test_endpoint_preco_por_commodity_existente(c)
    print("✔ test_endpoint_preco_por_commodity_existente passou.")
    test_endpoint_preco_por_commodity_inexistente(c)
    print("✔ test_endpoint_preco_por_commodity_inexistente passou.")
    print("TODOS OS TESTES DE PREÇOS PÚBLICOS E CATÁLOGO PASSARAM COM SUCESSO!")




