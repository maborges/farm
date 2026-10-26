"""
Testes unitários e de integração para o serviço público de inteligência agropecuária IBGE/SIDRA.
Garante:
1. Catálogo homologado de 23 produtos agropecuários e 27 UFs.
2. Whitelist estrita e rejeição de parâmetros inválidos (anti-SSRF / URL arbitrária).
3. Regras LSPA vs PAM (LSPA restrito a Brasil e UF, apenas para culturas elegíveis).
4. Parsing semântico de respostas SIDRA (tradução de '-' para 0.0, '...' e 'X' para None).
5. Avaliação de defasagem (staleness) e status de disponibilidade (NORMAL, DEFASADO, SEM_DADOS).
6. Cache de 2 níveis (Redis L2 + Memória L1) e lock atômico single-flight.
7. Fallback transparente com dados anteriores em caso de falha externa.
8. Consulta de municípios por UF com cache estendido (7 dias).
9. Endpoints FastAPI sem JWT, sem sessão de banco e com headers de cache apropriados.
10. Rate limiting por IP.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from core.config import settings
from public_mercado.sidra import (
    PRODUTOS,
    UFS,
    ConsultaSidra,
    IbgeSidraClient,
    normalizar_periodo,
    parse_resposta_sidra,
    parse_valor_sidra,
)
from public_mercado.sidra_cache import SidraCache
from public_mercado.sidra_service import IbgeSidraService

SAMPLE_SIDRA_PAM = [
    {
        "NC": "Nível Territorial (Código)",
        "NN": "Nível Territorial",
        "MC": "Unidade de Medida (Código)",
        "MN": "Unidade de Medida",
        "V": "Valor",
        "D1C": "Brasil (Código)",
        "D1N": "Brasil",
        "D2C": "Variável (Código)",
        "D2N": "Variável",
        "D3C": "Ano (Código)",
        "D3N": "Ano",
        "D4C": "Produto das lavouras temporárias e permanentes (Código)",
        "D4N": "Produto das lavouras temporárias e permanentes",
    },
    {
        "NC": "1",
        "NN": "Brasil",
        "MC": "1006",
        "MN": "Toneladas",
        "V": "150000000",
        "D1C": "1",
        "D1N": "Brasil",
        "D2C": "214",
        "D2N": "Quantidade produzida",
        "D3C": "2024",
        "D3N": "2024",
        "D4C": "40124",
        "D4N": "Soja (em grão)",
    },
    {
        "NC": "1",
        "NN": "Brasil",
        "MC": "1018",
        "MN": "Hectares",
        "V": "45000000",
        "D1C": "1",
        "D1N": "Brasil",
        "D2C": "216",
        "D2N": "Área colhida",
        "D3C": "2024",
        "D3N": "2024",
        "D4C": "40124",
        "D4N": "Soja (em grão)",
    },
    {
        "NC": "1",
        "NN": "Brasil",
        "MC": "1018",
        "MN": "Hectares",
        "V": "-",
        "D1C": "1",
        "D1N": "Brasil",
        "D2C": "8331",
        "D2N": "Área plantada ou destinada à colheita",
        "D3C": "2024",
        "D3N": "2024",
        "D4C": "40124",
        "D4N": "Soja (em grão)",
    },
    {
        "NC": "1",
        "NN": "Brasil",
        "MC": "1025",
        "MN": "Quilogramas por Hectare",
        "V": "...",
        "D1C": "1",
        "D1N": "Brasil",
        "D2C": "112",
        "D2N": "Rendimento médio da produção",
        "D3C": "2024",
        "D3N": "2024",
        "D4C": "40124",
        "D4N": "Soja (em grão)",
    },
]

SAMPLE_MUNICIPIOS_RAW = [
    {"id": 3550308, "nome": "São Paulo"},
    {"id": 3509502, "nome": "Campinas"},
    {"id": 3543402, "nome": "Ribeirão Preto"},
]


@pytest.fixture
def memory_sidra_cache() -> SidraCache:
    cache = SidraCache(redis_url="redis://localhost:9999/0", single_worker_fallback=True)
    cache.redis_ready = AsyncMock(return_value=False)
    return cache


def make_mock_client_sidra(
    valores_data: Any = None,
    modificacoes_data: Any = None,
    municipios_data: Any = None,
    side_effect: Exception | None = None,
) -> httpx.AsyncClient:
    mock = MagicMock(spec=httpx.AsyncClient)
    if side_effect:
        mock.get.side_effect = side_effect
    else:
        async def fake_get(url: str, **kwargs: Any) -> httpx.Response:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            if "localidades/estados" in url:
                data = municipios_data or SAMPLE_MUNICIPIOS_RAW
            elif "modificacoes" in url or "periodos" in url:
                data = modificacoes_data or [{"id": "2024", "modificacao": "15/10/2024"}]
            else:
                data = valores_data or SAMPLE_SIDRA_PAM

            resp.text = json.dumps(data)
            resp.content = resp.text.encode()
            resp.json.return_value = data
            return resp

        mock.get.side_effect = fake_get
    return mock


# 1. Parsing semântico de valores e períodos
def test_parsing_valores_e_periodos():
    assert parse_valor_sidra("150.5") == (150.5, None)
    assert parse_valor_sidra("150000000") == (150000000.0, None)
    assert parse_valor_sidra("-") == (0.0, "-")
    assert parse_valor_sidra("...") == (None, "...")
    assert parse_valor_sidra("X") == (None, "X")

    assert normalizar_periodo("2024") == "2024"
    assert normalizar_periodo("202408") == "2024-08"


# 2. Parsing de resposta estruturada SIDRA
def test_parse_resposta_sidra():
    consulta = ConsultaSidra(
        produto=PRODUTOS["soja"],
        nivel="BRASIL",
        codigo="all",
        periodo="2024",
        fonte=PRODUTOS["soja"].fonte,
        categorias=(PRODUTOS["soja"].categoria,),
    )
    nome_local, indicadores = parse_resposta_sidra(SAMPLE_SIDRA_PAM, consulta)
    assert nome_local == "Brasil"
    assert len(indicadores) == 4

    prod = next(i for i in indicadores if i.id == "PRODUCAO")
    assert prod.ultimoValor == 150000000.0
    assert prod.unidade == "Toneladas"
    assert prod.ultimoPeriodo == "2024"

    area_colhida = next(i for i in indicadores if i.id == "AREA_COLHIDA")
    assert area_colhida.ultimoValor == 45000000.0

    area_plantada = next(i for i in indicadores if i.id == "AREA_PLANTADA")
    assert area_plantada.ultimoValor == 0.0  # '-' convertido para 0.0

    rendimento = next(i for i in indicadores if i.id == "RENDIMENTO_MEDIO")
    assert rendimento.ultimoValor is None  # '...' convertido para None


# 3. Whitelist e validação de parâmetros
@pytest.mark.asyncio
async def test_whitelist_e_rejeicao_parametros(memory_sidra_cache: SidraCache):
    service = IbgeSidraService(cache=memory_sidra_cache, client=IbgeSidraClient())

    # Produto inválido
    with pytest.raises(ValueError, match="não homologado"):
        await service.get_estatisticas(produto_id="criptoativo")

    # UF inválida
    with pytest.raises(ValueError, match="não homologado"):
        await service.get_estatisticas(produto_id="soja", nivel="UF", uf="XX")

    # Município com formato inválido (deve ter 7 dígitos)
    with pytest.raises(ValueError, match="deve possuir 7 dígitos"):
        await service.get_estatisticas(produto_id="soja", nivel="MUNICIPIO", municipio="12345")

    # Município com prefixo de UF inexistente
    with pytest.raises(ValueError, match="Prefixo de UF '99'"):
        await service.get_estatisticas(produto_id="soja", nivel="MUNICIPIO", municipio="9912345")

    # LSPA não suportado no nível de município
    with pytest.raises(ValueError, match="O LSPA não possui desagregação por município"):
        await service.get_estatisticas(
            produto_id="soja",
            nivel="MUNICIPIO",
            municipio="3550308",
            fonte_override="LSPA",
        )

    # LSPA não suportado para pecuária
    with pytest.raises(ValueError, match="não possui série no LSPA"):
        await service.get_estatisticas(
            produto_id="bovinos",
            nivel="BRASIL",
            fonte_override="LSPA",
        )


# 4. Catálogo homologado de produtos e UFs
def test_catalogo_ibge(memory_sidra_cache: SidraCache):
    service = IbgeSidraService(cache=memory_sidra_cache, client=IbgeSidraClient())
    catalogo = service.get_catalogo()

    assert len(catalogo.produtos) == len(PRODUTOS)
    assert len(catalogo.ufs) == 27
    assert any(p.id == "soja" for p in catalogo.produtos)
    assert any(p.id == "milho" for p in catalogo.produtos)
    assert any(p.id == "bovinos" for p in catalogo.produtos)
    assert any(p.id == "leite" for p in catalogo.produtos)

    soja = next(p for p in catalogo.produtos if p.id == "soja")
    assert soja.suportaLspa is True

    bovinos = next(p for p in catalogo.produtos if p.id == "bovinos")
    assert bovinos.suportaLspa is False


# 5. Consulta e cache de municípios
@pytest.mark.asyncio
async def test_municipios_uf_e_cache(memory_sidra_cache: SidraCache):
    mock_http = make_mock_client_sidra()
    service = IbgeSidraService(cache=memory_sidra_cache, client=IbgeSidraClient(client=mock_http))

    # Primeira consulta (miss)
    resp1 = await service.get_municipios("35")
    assert resp1.sucesso is True
    assert len(resp1.itens) == 3
    assert resp1.itens[0].nome == "Campinas"  # Ordenado alfabeticamente

    # Segunda consulta (hit)
    mock_http.get.reset_mock()
    resp2 = await service.get_municipios("35")
    assert resp2.sucesso is True
    assert len(resp2.itens) == 3
    assert mock_http.get.call_count == 0  # Servido pelo cache


# 6. Fluxo de consulta de estatísticas com sucesso e cache
@pytest.mark.asyncio
async def test_consulta_estatisticas_sucesso(memory_sidra_cache: SidraCache):
    mock_http = make_mock_client_sidra()
    service = IbgeSidraService(cache=memory_sidra_cache, client=IbgeSidraClient(client=mock_http))

    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    res = await service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now)

    assert res.sucesso is True
    assert res.produto.id == "soja"
    assert res.localidade.nivel == "BRASIL"
    assert len(res.indicadores) == 4
    assert res.estadoDisponibilidade in ("NORMAL", "DEFASADO")

    # Segunda consulta deve bater no cache
    mock_http.get.reset_mock()
    res2 = await service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now)
    assert res2.sucesso is True
    assert mock_http.get.call_count == 0


# 7. Fallback transparente com dados anteriores em caso de falha da API
@pytest.mark.asyncio
async def test_fallback_transparente_em_falha(memory_sidra_cache: SidraCache):
    mock_http = make_mock_client_sidra()
    service = IbgeSidraService(cache=memory_sidra_cache, client=IbgeSidraClient(client=mock_http))

    now1 = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    res1 = await service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now1)
    assert res1.sucesso is True

    # Simula falha subsequente do IBGE
    mock_failing_http = make_mock_client_sidra(side_effect=httpx.ConnectError("IBGE timeout"))
    failing_service = IbgeSidraService(cache=memory_sidra_cache, client=IbgeSidraClient(client=mock_failing_http))

    # Limpa fresh cache para forçar tentativa na API
    memory_sidra_cache.local_fresh.clear()

    now2 = datetime(2026, 10, 19, 15, 0, 0, tzinfo=timezone.utc)
    res2 = await failing_service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now2)

    assert res2.sucesso is True
    assert res2.estadoDisponibilidade == "FONTE_INDISPONIVEL"
    assert res2.estaDesatualizado is True
    # Valores preservados do fallback
    assert len(res2.indicadores) == 4
    prod = next(i for i in res2.indicadores if i.id == "PRODUCAO")
    assert prod.ultimoValor == 150000000.0


# 8. Single-flight lock em concorrência
@pytest.mark.asyncio
async def test_single_flight_lock(memory_sidra_cache: SidraCache):
    call_counter = 0

    async def slow_get(url: str, **kwargs: Any) -> httpx.Response:
        nonlocal call_counter
        call_counter += 1
        await asyncio.sleep(0.05)
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        data: Any = [] if "periodos" in url or "modificacoes" in url else SAMPLE_SIDRA_PAM
        resp.text = json.dumps(data)
        resp.content = resp.text.encode()
        resp.json.return_value = data
        return resp

    mock_http = MagicMock(spec=httpx.AsyncClient)
    mock_http.get.side_effect = slow_get
    service = IbgeSidraService(cache=memory_sidra_cache, client=IbgeSidraClient(client=mock_http))

    # Dispara 5 requisições simultâneas
    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    results = await asyncio.gather(
        service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now),
        service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now),
        service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now),
        service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now),
        service.get_estatisticas("soja", nivel="BRASIL", anos=3, now=now),
    )

    for r in results:
        assert r.sucesso is True
    # Apenas uma requisição primária deve ter batido no endpoint SIDRA
    assert call_counter <= 2  # 1 valores + 1 modificações


# 9. Testes de API FastAPI (sem banco de dados, sem JWT, com Cache-Control)
def test_endpoints_fastapi_sem_auth():
    from main import app

    client = TestClient(app)

    # 1. Catálogo
    resp_cat = client.get("/api/v1/public/mercado/ibge/catalogo")
    assert resp_cat.status_code == 200
    data_cat = resp_cat.json()
    assert len(data_cat["produtos"]) == 23
    assert len(data_cat["ufs"]) == 27
    assert "public, max-age=3600" in resp_cat.headers.get("Cache-Control", "")

    # 2. Estatísticas com parâmetros inválidos
    resp_err = client.get("/api/v1/public/mercado/ibge/estatisticas?produto=nao_existe")
    assert resp_err.status_code == 400
    assert "não homologado" in resp_err.json()["detail"]

    # 3. Municípios com UF inválida
    resp_uf_err = client.get("/api/v1/public/mercado/ibge/municipios/99")
    assert resp_uf_err.status_code == 400


# 10. Rate limiting por IP
@pytest.mark.asyncio
async def test_rate_limiting_por_ip(memory_sidra_cache: SidraCache):
    bucket = "test_ip_hash_123"
    shared = False

    # Consome os primeiros 60 requests
    for _ in range(60):
        allowed = await memory_sidra_cache.allow_request(bucket, shared)
        assert allowed is True

    # O 61º request deve ser bloqueado
    blocked = await memory_sidra_cache.allow_request(bucket, shared)
    assert blocked is False
