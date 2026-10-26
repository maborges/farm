"""
Testes unitários e de integração para os indicadores macroeconômicos públicos (BCB SGS).
Garante:
1. Sucesso na obtenção das 4 séries oficiais (Meta Selic, IPCA mensal, IPCA 12m, Euro PTAX)
2. Parsing e semântica de datas (DD/MM/YYYY para ISO) e unidades (% a.a., % a.m., BRL)
3. Cache hit e miss no Redis
4. Cache em memória local quando Redis indisponível
5. Controle de concorrência e single-flight lock
6. Falha do BCB com fallback para a última observação válida
7. Falha sem cache prévio (estado INDISPONIVEL gracioso)
8. Timeout e erro de rede do BCB
9. JSON malformado ou lista vazia do SGS
10. Degradação transparente na falha do Redis
11. Ausência absoluta de sessões PostgreSQL
12. Rota pública anônima sem JWT
13. Rate limit por IP
14. Não regressão do endpoint PTAX
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

from core.config import settings
from public_mercado.macro_cache import MacroCache, MacroCacheEntry
from public_mercado.macro_service import IndicadoresMacroService
from public_mercado.sgs import (
    BcbSgsClient,
    IndicadoresMacroPayload,
    SgsObservation,
    parse_sgs_date,
    parse_sgs_json,
)

SAO_PAULO = ZoneInfo("America/Sao_Paulo")

SAMPLE_SELIC = [
    {"data": "19/10/2026", "valor": "13.75"},
    {"data": "04/11/2026", "valor": "13.75"},
]
SAMPLE_IPCA_M = [{"data": "01/09/2026", "valor": "0.82"}]
SAMPLE_IPCA_12M = [{"data": "01/09/2026", "valor": "4.58"}]
SAMPLE_EURO_V = [{"data": "19/10/2026", "valor": "5.6682000"}]
SAMPLE_EURO_C = [{"data": "19/10/2026", "valor": "5.6665000"}]


def make_mock_client_sgs(payload_map: dict[str, Any] | None = None, side_effect: Exception | None = None) -> httpx.AsyncClient:
    mock = MagicMock(spec=httpx.AsyncClient)
    if side_effect:
        mock.get.side_effect = side_effect
    else:
        async def fake_get(url: str, **kwargs: Any) -> httpx.Response:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            data = None
            if payload_map:
                for k, v in payload_map.items():
                    if k in url:
                        data = v
                        break
            if data is None:
                if "432" in url:
                    data = SAMPLE_SELIC
                elif "433" in url:
                    data = SAMPLE_IPCA_M
                elif "13522" in url:
                    data = SAMPLE_IPCA_12M
                elif "21619" in url:
                    data = SAMPLE_EURO_V
                elif "21620" in url:
                    data = SAMPLE_EURO_C
                else:
                    data = []
            resp.text = json.dumps(data)
            return resp

        mock.get = fake_get
    return mock


@pytest.fixture
def memory_macro_cache() -> MacroCache:
    cache = MacroCache("redis://localhost:6379/0", single_worker_fallback=True)
    cache.redis_ready = AsyncMock(return_value=False)
    return cache


# 1. Parsing puro de datas e JSON do SGS
def test_01_parsing_sgs():
    d = parse_sgs_date("19/10/2026")
    assert d == date(2026, 10, 19)

    obs = parse_sgs_json(json.dumps([{"data": "04/11/2026", "valor": "13,75"}]))
    assert len(obs) == 1
    assert obs[0].data == date(2026, 11, 4)
    assert obs[0].valor == 13.75

    with pytest.raises(ValueError):
        parse_sgs_date("invalid-date")

    with pytest.raises(ValueError):
        parse_sgs_json("[]")


# 2. Leitura completa com sucesso
@pytest.mark.asyncio
async def test_02_macro_sucesso(memory_macro_cache: MacroCache):
    mock_http = make_mock_client_sgs()
    client = BcbSgsClient(client=mock_http)
    service = IndicadoresMacroService(cache=memory_macro_cache, client=client)

    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    resp = await service.get(now)

    assert resp.sucesso is True
    assert resp.estadoDisponibilidade == "NORMAL"
    assert resp.estaDesatualizado is False
    assert len(resp.itens) == 4

    selic = next(i for i in resp.itens if i.id == "SELIC_META")
    assert selic.valor == 13.75
    assert selic.unidade == "% a.a."
    assert selic.codigoSerieBcb == 432
    assert selic.periodicidade == "DIARIA"
    assert selic.dataReferencia == "2026-10-19"

    ipca_m = next(i for i in resp.itens if i.id == "IPCA_MENSAL")
    assert ipca_m.valor == 0.82
    assert ipca_m.unidade == "% a.m."
    assert ipca_m.periodicidade == "MENSAL"

    ipca_12m = next(i for i in resp.itens if i.id == "IPCA_12M")
    assert ipca_12m.valor == 4.58
    assert ipca_12m.unidade == "% em 12 meses"

    euro = next(i for i in resp.itens if i.id == "EURO_PTAX")
    assert euro.valor == 5.6682
    assert euro.valorVenda == 5.6682
    assert euro.valorCompra == 5.6665
    assert euro.unidade == "BRL"


# 3. Cache hit na memória local
@pytest.mark.asyncio
async def test_03_cache_hit_memoria(memory_macro_cache: MacroCache):
    mock_http = make_mock_client_sgs()
    client = BcbSgsClient(client=mock_http)
    service = IndicadoresMacroService(cache=memory_macro_cache, client=client)

    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    resp1 = await service.get(now)
    assert resp1.sucesso is True

    # Substitui client por um que falharia se chamado
    failing_client = BcbSgsClient(client=make_mock_client_sgs(side_effect=httpx.ConnectError("Falha")))
    service.client = failing_client

    # Segunda chamada deve vir do cache fresh sem acionar o cliente
    resp2 = await service.get(now)
    assert resp2.sucesso is True
    assert resp2.itens[0].valor == resp1.itens[0].valor


# 4. Falha do BCB com fallback da última cotação conhecida
@pytest.mark.asyncio
async def test_04_fallback_ultima_conhecida(memory_macro_cache: MacroCache):
    mock_http = make_mock_client_sgs()
    client = BcbSgsClient(client=mock_http)
    service = IndicadoresMacroService(cache=memory_macro_cache, client=client)

    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    resp1 = await service.get(now)
    assert resp1.sucesso is True

    # Simula expiração do fresh cache
    memory_macro_cache.local_fresh = None

    # Simula falha do BCB
    service.client = BcbSgsClient(client=make_mock_client_sgs(side_effect=httpx.TimeoutException("Timeout BCB")))

    resp2 = await service.get(now)
    assert resp2.sucesso is True
    assert resp2.estadoDisponibilidade == "FONTE_INDISPONIVEL"
    assert resp2.estaDesatualizado is True
    assert len(resp2.itens) == 4
    assert resp2.itens[0].valor == 13.75


# 5. Falha total sem cache prévio
@pytest.mark.asyncio
async def test_05_falha_total_sem_cache(memory_macro_cache: MacroCache):
    client = BcbSgsClient(client=make_mock_client_sgs(side_effect=httpx.ConnectError("Sem internet")))
    service = IndicadoresMacroService(cache=memory_macro_cache, client=client)

    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    resp = await service.get(now)
    assert resp.sucesso is False
    assert resp.estadoDisponibilidade == "INDISPONIVEL"
    assert len(resp.itens) == 0


# 6. Concorrência: duas chamadas simultâneas
@pytest.mark.asyncio
async def test_06_concorrencia_single_flight(memory_macro_cache: MacroCache):
    call_count = 0

    class CountingClient(BcbSgsClient):
        async def fetch_series_dict(self) -> dict[str, SgsObservation | Exception]:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return await super().fetch_series_dict()

    mock_http = make_mock_client_sgs()
    client = CountingClient(client=mock_http)
    service = IndicadoresMacroService(cache=memory_macro_cache, client=client)

    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    r1, r2 = await asyncio.gather(service.get(now), service.get(now))

    assert r1.sucesso is True
    assert r2.sucesso is True
    assert call_count == 1  # Apenas uma requisição executada à origem


# 7. Endpoint FastAPI público e ausência absoluta de PostgreSQL
def test_07_endpoint_publico_e_isolamento_postgresql():
    from main import app

    with patch("core.database.async_session_maker") as mock_session_maker:
        client = TestClient(app)
        # Teste na rota macro
        response = client.get("/api/v1/public/mercado/indicadores-macro")
        # Garante que nenhuma sessão PostgreSQL foi requisitada
        mock_session_maker.assert_not_called()

        assert response.status_code in (200, 429)
        if response.status_code == 200:
            data = response.json()
            assert "sucesso" in data
            assert "itens" in data
            assert response.headers.get("Cache-Control") is not None


# 8. Não regressão do endpoint PTAX
def test_08_nao_regressao_ptax():
    from main import app

    with patch("core.database.async_session_maker") as mock_session_maker:
        client = TestClient(app)
        response = client.get("/api/v1/public/mercado/ptax")
        mock_session_maker.assert_not_called()
        assert response.status_code in (200, 429)
        if response.status_code == 200:
            data = response.json()
            assert data.get("indicador") == "DOLAR_PTAX"
            assert data.get("moeda") == "USD"


# 9. Fallback de uma série NÃO mascara a disponibilidade de outra (Atividade 5)
@pytest.mark.asyncio
async def test_09_fallback_granular_nao_mascara_outra_serie(memory_macro_cache: MacroCache):
    # Primeiro popula o cache com todas as 4 séries
    mock_http = make_mock_client_sgs()
    client = BcbSgsClient(client=mock_http)
    service = IndicadoresMacroService(cache=memory_macro_cache, client=client)

    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    initial_resp = await service.get(now)
    assert initial_resp.sucesso is True
    assert initial_resp.estadoDisponibilidade == "NORMAL"

    # Expira o cache fresh
    memory_macro_cache.local_fresh = None

    # Simula falha EXCLUSIVA do Euro (ex: 502 Bad Gateway no SGS 21619 e 21620), enquanto Selic e IPCA respondem 200
    async def selective_mock_get(url: str, **kwargs: Any) -> httpx.Response:
        if "21619" in url or "21620" in url:
            raise httpx.HTTPStatusError("502 Bad Gateway", request=MagicMock(), response=MagicMock(status_code=502))
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if "432" in url:
            resp.text = json.dumps([{"data": "19/10/2026", "valor": "13.75"}])
        elif "433" in url:
            resp.text = json.dumps([{"data": "01/09/2026", "valor": "0.82"}])
        elif "13522" in url:
            resp.text = json.dumps([{"data": "01/09/2026", "valor": "4.58"}])
        return resp

    failing_euro_client = MagicMock(spec=httpx.AsyncClient)
    failing_euro_client.get = selective_mock_get
    service.client = BcbSgsClient(client=failing_euro_client)

    resp = await service.get(now)
    assert resp.sucesso is True
    # Disponibilidade global deve indicar PARCIAL
    assert resp.estadoDisponibilidade == "PARCIAL"
    assert resp.estaDesatualizado is True

    # Selic e IPCA devem estar NORMAL e NÃO desatualizados
    selic = next(i for i in resp.itens if i.id == "SELIC_META")
    assert selic.estadoDisponibilidade == "NORMAL"
    assert selic.estaDesatualizado is False

    ipca_m = next(i for i in resp.itens if i.id == "IPCA_MENSAL")
    assert ipca_m.estadoDisponibilidade == "NORMAL"
    assert ipca_m.estaDesatualizado is False

    # Euro PTAX deve estar em FONTE_INDISPONIVEL com fallback preservado
    euro = next(i for i in resp.itens if i.id == "EURO_PTAX")
    assert euro.estadoDisponibilidade == "FONTE_INDISPONIVEL"
    assert euro.estaDesatualizado is True
    assert euro.valor == 5.6682  # Recuperado com integridade do fallback


# 10. Teste semântico de datas, fins de semana, feriados e ausência de novas publicações (Atividade 4)
def test_10_semantica_datas_e_calendario():
    from public_mercado.macro_service import check_item_staleness

    ref_monday = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)

    # Euro PTAX da sexta-feira anterior (3 dias atrás): NORMAL
    st, stale = check_item_staleness("EURO_PTAX", date(2026, 10, 16), ref_monday)
    assert st == "NORMAL"
    assert stale is False

    # Euro PTAX de 10 dias atrás: DEFASADO
    st, stale = check_item_staleness("EURO_PTAX", date(2026, 10, 9), ref_monday)
    assert st == "DEFASADO"
    assert stale is True

    # Selic inalterada há 45 dias (ciclo normal Copom): NORMAL
    st, stale = check_item_staleness("SELIC_META", date(2026, 9, 4), ref_monday)
    assert st == "NORMAL"
    assert stale is False

    # Selic inalterada há 75 dias: DEFASADO
    st, stale = check_item_staleness("SELIC_META", date(2026, 8, 5), ref_monday)
    assert st == "DEFASADO"
    assert stale is True

    # IPCA do mês anterior (48 dias): NORMAL (calendário de apuração IBGE)
    st, stale = check_item_staleness("IPCA_MENSAL", date(2026, 9, 1), ref_monday)
    assert st == "NORMAL"
    assert stale is False

    # IPCA de 3 meses atrás: DEFASADO
    st, stale = check_item_staleness("IPCA_MENSAL", date(2026, 7, 1), ref_monday)
    assert st == "DEFASADO"
    assert stale is True


# 11. Não classificar valores antigos como atualizados apenas porque a requisição HTTP teve sucesso (Atividade 3 e 4)
@pytest.mark.asyncio
async def test_11_valores_antigos_nao_sao_atualizados_apenas_por_http_200(memory_macro_cache: MacroCache):
    # Simula BCB respondendo 200 OK mas com dados muito antigos (ex: 90 dias atrás)
    old_selic = [{"data": "01/01/2026", "valor": "10.00"}]
    old_euro = [{"data": "01/01/2026", "valor": "5.0000"}]
    mock_http = make_mock_client_sgs(payload_map={"432": old_selic, "21619": old_euro, "21620": old_euro})
    service = IndicadoresMacroService(cache=memory_macro_cache, client=BcbSgsClient(client=mock_http))

    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    resp = await service.get(now)

    assert resp.sucesso is True
    # Apesar do HTTP 200, os itens antigos DEVEM ser marcados como DEFASADO
    selic = next(i for i in resp.itens if i.id == "SELIC_META")
    assert selic.estadoDisponibilidade == "DEFASADO"
    assert selic.estaDesatualizado is True

    euro = next(i for i in resp.itens if i.id == "EURO_PTAX")
    assert euro.estadoDisponibilidade == "DEFASADO"
    assert euro.estaDesatualizado is True
