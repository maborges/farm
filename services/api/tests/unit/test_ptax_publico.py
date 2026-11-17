"""
Testes unitários e de integração para a PTAX pública do DeepFarms Agro.
Cobre todos os 15 cenários mandatórios da etapa DEEPFARMS-AGRO-FREE-01E2B:
1. Fechamento disponível
2. Dia anterior / Manhã antes do fechamento
3. Fim de semana
4. Feriado
5. Lista vazia do BCB
6. Timeout do BCB
7. HTTP 429 e 500 do BCB
8. JSON inválido / malformado
9. Cache hit e miss
10. Cache expirado
11. Concorrência (chamadas simultâneas)
12. Falha de Redis / Degradação transparente
13. Ausência absoluta de acesso PostgreSQL
14. Endpoint anônimo (sem token JWT)
15. Não regressão comercial
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

from core.config import settings
from main import app
from public_mercado.cache import CacheEntry, PtaxCache
from public_mercado.ptax import BcbPtaxClient, PtaxQuote, SAO_PAULO
from public_mercado.service import PtaxService

SAMPLE_CLOSING_JSON = {
    "@odata.context": "https://was-p.bcnet.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata$metadata#_CotacaoDolarPeriodo",
    "value": [
        {
            "cotacaoCompra": 5.6372,
            "cotacaoVenda": 5.6378,
            "dataHoraCotacao": "2024-10-15 13:06:27.393",
        }
    ],
}


def make_mock_client(status_code: int = 200, payload: Any = None, side_effect: Exception | None = None) -> httpx.AsyncClient:
    mock = MagicMock(spec=httpx.AsyncClient)
    if side_effect:
        mock.stream.side_effect = side_effect
        mock.get.side_effect = side_effect
    else:
        resp = MagicMock()
        resp.status_code = status_code
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            resp.raise_for_status.side_effect = httpx.HTTPStatusError("Error", request=MagicMock(), response=resp)

        async def aiter_bytes():
            yield json.dumps(payload).encode("utf-8") if payload is not None else b""

        resp.aiter_bytes = aiter_bytes
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=resp)
        cm.__aexit__ = AsyncMock(return_value=None)
        mock.stream.return_value = cm
    return mock


@pytest.fixture
def memory_cache() -> PtaxCache:
    cache = PtaxCache("redis://localhost:6379/0", single_worker_fallback=True)
    cache.redis_ready = AsyncMock(return_value=False)
    return cache


# 1. Fechamento disponível
@pytest.mark.asyncio
async def test_01_fechamento_disponivel(memory_cache: PtaxCache):
    mock_http = make_mock_client(200, SAMPLE_CLOSING_JSON)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client)

    now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)
    resp = await service.get(now)

    assert resp.sucesso is True
    assert resp.cotacaoCompra == 5.6372
    assert resp.cotacaoVenda == 5.6378
    assert resp.dataCotacao == "2024-10-15"
    assert resp.estadoDisponibilidade == "NORMAL"
    assert resp.estadoCotacao == "ULTIMO_FECHAMENTO_OFICIAL"
    assert resp.estaDesatualizado is False


# 2. Dia anterior / Manhã antes do fechamento
@pytest.mark.asyncio
async def test_02_dia_anterior_antes_fechamento(memory_cache: PtaxCache):
    # Simula consulta às 09:00 do dia 16/10, quando a última cotação disponível no BCB é 15/10
    mock_http = make_mock_client(200, SAMPLE_CLOSING_JSON)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client)

    now = datetime(2024, 10, 16, 9, 0, 0, tzinfo=SAO_PAULO)
    resp = await service.get(now)

    assert resp.sucesso is True
    assert resp.dataCotacao == "2024-10-15"
    assert resp.estadoDisponibilidade == "NORMAL"


# 3. Fim de semana (sábado/domingo)
@pytest.mark.asyncio
async def test_03_fim_de_semana(memory_cache: PtaxCache):
    # No sábado 19/10, o BCB retorna o fechamento de sexta 18/10
    friday_json = {
        "value": [
            {
                "cotacaoCompra": 5.6510,
                "cotacaoVenda": 5.6516,
                "dataHoraCotacao": "2024-10-18 13:05:00.000",
            }
        ]
    }
    mock_http = make_mock_client(200, friday_json)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client)

    saturday = datetime(2024, 10, 19, 15, 0, 0, tzinfo=SAO_PAULO)
    resp = await service.get(saturday)

    assert resp.sucesso is True
    assert resp.cotacaoCompra == 5.6510
    assert resp.dataCotacao == "2024-10-18"


# 4. Feriado nacional
@pytest.mark.asyncio
async def test_04_feriado_nacional(memory_cache: PtaxCache):
    # Feriado nacional no meio da semana: entrega a última cotação anterior
    holiday_json = {
        "value": [
            {
                "cotacaoCompra": 5.6000,
                "cotacaoVenda": 5.6010,
                "dataHoraCotacao": "2024-11-14 13:10:00.000",
            }
        ]
    }
    mock_http = make_mock_client(200, holiday_json)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client)

    holiday = datetime(2024, 11, 15, 14, 0, 0, tzinfo=SAO_PAULO)
    resp = await service.get(holiday)

    assert resp.sucesso is True
    assert resp.dataCotacao == "2024-11-14"


# 5. Lista vazia do BCB
@pytest.mark.asyncio
async def test_05_lista_vazia(memory_cache: PtaxCache):
    empty_json = {"value": []}
    mock_http = make_mock_client(200, empty_json)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client)

    now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)
    resp = await service.get(now)

    assert resp.sucesso is False
    assert resp.cotacaoCompra is None
    assert resp.estadoDisponibilidade == "INDISPONIVEL"


# 6. Timeout do BCB
@pytest.mark.asyncio
async def test_06_timeout_bcb(memory_cache: PtaxCache):
    mock_http = make_mock_client(side_effect=httpx.TimeoutException("Timeout after 12s"))
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client)

    now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)
    resp = await service.get(now)

    assert resp.sucesso is False
    assert resp.estadoDisponibilidade == "INDISPONIVEL"


# 7. HTTP 429 e 500 do BCB
@pytest.mark.asyncio
async def test_07_http_429_e_500(memory_cache: PtaxCache):
    for status_code in (429, 500):
        mock_http = make_mock_client(status_code=status_code, payload={"error": "Erro BCB"})
        client = BcbPtaxClient(client=mock_http)
        service = PtaxService(cache=memory_cache, client=client)

        now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)
        resp = await service.get(now)
        assert resp.sucesso is False
        assert resp.estadoDisponibilidade == "INDISPONIVEL"


# 8. JSON inválido / malformado
@pytest.mark.asyncio
async def test_08_json_malformado(memory_cache: PtaxCache):
    mock = MagicMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()

    async def bad_bytes():
        yield b"/*{ 500: Erro desconhecido"

    resp.aiter_bytes = bad_bytes
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=None)
    mock.stream.return_value = cm

    client = BcbPtaxClient(client=mock)
    service = PtaxService(cache=memory_cache, client=client)

    now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)
    resp = await service.get(now)

    assert resp.sucesso is False
    assert resp.estadoDisponibilidade == "INDISPONIVEL"


# 9. Cache hit vs miss
@pytest.mark.asyncio
async def test_09_cache_hit_miss(memory_cache: PtaxCache):
    mock_http = make_mock_client(200, SAMPLE_CLOSING_JSON)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client, ttl_seconds=300)

    now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)
    # Miss
    resp1 = await service.get(now)
    assert resp1.sucesso is True
    assert mock_http.stream.call_count == 1

    # Hit (segunda chamada não deve chamar o HTTP)
    resp2 = await service.get(now)
    assert resp2.sucesso is True
    assert mock_http.stream.call_count == 1


# 10. Cache expirado
@pytest.mark.asyncio
async def test_10_cache_expirado(memory_cache: PtaxCache):
    mock_http = make_mock_client(200, SAMPLE_CLOSING_JSON)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client, ttl_seconds=60)

    now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)
    await service.get(now)
    assert mock_http.stream.call_count == 1

    # Simula passagem de tempo acima do TTL
    memory_cache.local_fresh = (memory_cache.local_fresh[0], 0.0)

    await service.get(now + timedelta(seconds=120))
    assert mock_http.stream.call_count == 2


# 11. Concorrência (chamadas simultâneas)
@pytest.mark.asyncio
async def test_11_concorrencia(memory_cache: PtaxCache):
    mock_http = make_mock_client(200, SAMPLE_CLOSING_JSON)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=memory_cache, client=client)

    now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)

    # Dispara 10 chamadas concorrentes
    tasks = [service.get(now) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert all(r.sucesso for r in results)
    # Apenas 1 chamada deve ter batido no mock do BCB graças ao lock/single-flight
    assert mock_http.stream.call_count == 1


# 12. Falha de Redis / Degradação transparente
@pytest.mark.asyncio
async def test_12_degradacao_falha_redis():
    cache = PtaxCache("redis://unreachable:6379/0", single_worker_fallback=True)
    assert await cache.redis_ready() is False

    mock_http = make_mock_client(200, SAMPLE_CLOSING_JSON)
    client = BcbPtaxClient(client=mock_http)
    service = PtaxService(cache=cache, client=client)

    now = datetime(2024, 10, 15, 14, 0, 0, tzinfo=SAO_PAULO)
    resp = await service.get(now)

    assert resp.sucesso is True
    assert resp.cotacaoCompra == 5.6372


# 13. Ausência absoluta de acesso PostgreSQL
@pytest.mark.asyncio
async def test_13_ausencia_postgresql():
    with patch("core.database.async_session_maker") as mock_session_maker:
        client = TestClient(app)
        response = client.get("/api/v1/public/mercado/ptax")
        assert response.status_code in (200, 503)
        # async_session_maker NUNCA pode ser chamado
        mock_session_maker.assert_not_called()


# 14. Endpoint anônimo (sem token JWT)
def test_14_endpoint_anonimo():
    client = TestClient(app)
    # Requisição sem Authorization header
    response = client.get("/api/v1/public/mercado/ptax")
    assert response.status_code == 200
    data = response.json()
    assert data["indicador"] == "DOLAR_PTAX"
    assert data["moeda"] == "USD"
    assert data["fonteOficial"] == "Banco Central do Brasil (BCB)"


# 15. Não regressão comercial
def test_15_nao_regressao_rotas_comerciais():
    client = TestClient(app)
    # Rotas autenticadas do SaaS comercial continuam exigindo autenticação (401)
    res_team = client.get("/api/v1/team/users")
    assert res_team.status_code == 401
    res_cupons = client.get("/api/v1/backoffice/cupons")
    assert res_cupons.status_code == 401


def test_16_cors_permite_agro_na_rede_local_sem_liberar_origens_publicas():
    client = TestClient(app)
    allowed = client.options(
        "/api/v1/public/mercado/ptax",
        headers={
            "Origin": "http://192.168.0.3:3003",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/api/v1/public/mercado/ptax",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://192.168.0.3:3003"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
