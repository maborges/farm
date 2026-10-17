from __future__ import annotations

import asyncio
import inspect
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from public_mercado.cache import CacheEntry
from public_mercado.ptax import BCB_URL, BcbPtaxClient, PtaxQuote
from public_mercado.router import get_public_ptax
from public_mercado.service import PtaxService

NOW = datetime(2026, 10, 17, 15, 0, tzinfo=timezone.utc)


def payload(when: str = "2026-10-16 13:10:00.000", buy: object = 5.4321, sell: object = 5.4327) -> dict:
    return {"value": [{"cotacaoCompra": buy, "cotacaoVenda": sell, "dataHoraCotacao": when}]}


def client_for(response: httpx.Response | Exception, capture: dict | None = None) -> BcbPtaxClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture["request"] = request
        if isinstance(response, Exception):
            raise response
        return response

    return BcbPtaxClient(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


class MemoryCache:
    def __init__(self, fresh: CacheEntry | None = None, last: CacheEntry | None = None, shared: bool = True) -> None:
        self.fresh = fresh
        self.last = last
        self.shared = shared
        self.single_worker_fallback = not shared
        self.locked = False

    async def redis_ready(self) -> bool:
        return self.shared

    async def get_fresh(self, shared: bool) -> CacheEntry | None:
        return self.fresh

    async def get_last(self, shared: bool) -> CacheEntry | None:
        return self.last

    async def save(self, entry: CacheEntry, ttl: int, shared: bool) -> None:
        self.fresh = self.last = entry

    async def acquire(self, shared: bool) -> str | None:
        if self.locked:
            return None
        self.locked = True
        return "lock"

    async def release(self, token: str, shared: bool) -> None:
        self.locked = False


class CountingClient:
    def __init__(self, quote: PtaxQuote | None = None, error: Exception | None = None, delay: float = 0) -> None:
        self.quote = quote
        self.error = error
        self.delay = delay
        self.calls = 0

    async def fetch(self, now: datetime) -> PtaxQuote | None:
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.quote


def quote(days_ago: int = 1) -> PtaxQuote:
    return PtaxQuote(
        cotacaoCompra=5.4321,
        cotacaoVenda=5.4327,
        dataHoraBoletimIso=NOW - timedelta(days=days_ago),
    )


@pytest.mark.asyncio
async def test_cliente_consulta_serie_diaria_de_fechamento_com_janela_e_sem_credenciais() -> None:
    capture: dict = {}
    client = client_for(httpx.Response(200, json=payload()), capture)
    result = await client.fetch(NOW)
    await client.client.aclose()  # type: ignore[union-attr]

    request = capture["request"]
    assert str(request.url).startswith(BCB_URL)
    assert request.url.params["$orderby"] == "dataHoraCotacao desc"
    assert request.url.params["$top"] == "1"
    assert request.url.params["@dataFinalCotacao"] == "'10-17-2026'"
    assert "authorization" not in request.headers
    assert "cookie" not in request.headers
    assert "origin" not in request.headers
    assert result and result.dataHoraBoletimIso.utcoffset() == timedelta(hours=-3)


@pytest.mark.asyncio
@pytest.mark.parametrize("day", ["2026-10-17 13:10:00.000", "2026-10-18 13:10:00.000"])
async def test_cliente_aceita_ultimo_fechamento_em_fim_de_semana_quando_nao_futuro(day: str) -> None:
    reference = datetime.fromisoformat(day.replace(" ", "T")).replace(tzinfo=timezone(timedelta(hours=-3)))
    current = reference + timedelta(hours=2)
    client = client_for(httpx.Response(200, json=payload(day)))
    assert await client.fetch(current)
    await client.client.aclose()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_cliente_lista_vazia_representa_fechamento_ainda_nao_publicado() -> None:
    client = client_for(httpx.Response(200, json={"value": []}))
    assert await client.fetch(NOW) is None
    await client.client.aclose()  # type: ignore[union-attr]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response,error",
    [
        (httpx.Response(429), httpx.HTTPStatusError),
        (httpx.Response(500), httpx.HTTPStatusError),
        (httpx.Response(200, content=b"{"), json.JSONDecodeError),
    ],
)
async def test_cliente_rejeita_falhas_http_e_json(response: httpx.Response, error: type[Exception]) -> None:
    client = client_for(response)
    with pytest.raises(error):
        await client.fetch(NOW)
    await client.client.aclose()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_cliente_propaga_timeout_sem_retry() -> None:
    request = httpx.Request("GET", BCB_URL)
    client = client_for(httpx.ReadTimeout("timeout", request=request))
    with pytest.raises(httpx.ReadTimeout):
        await client.fetch(NOW)
    await client.client.aclose()  # type: ignore[union-attr]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"value": [{}]},
        payload(buy="NaN"),
        payload(buy=-1),
        payload(buy=6, sell=5),
        {"unexpected": []},
    ],
)
async def test_cliente_rejeita_campos_ausentes_e_valores_invalidos(body: dict) -> None:
    client = client_for(httpx.Response(200, json=body))
    with pytest.raises((ValueError, TypeError)):
        await client.fetch(NOW)
    await client.client.aclose()  # type: ignore[union-attr]


def test_modelo_rejeita_valores_nao_finitos() -> None:
    with pytest.raises(ValueError):
        PtaxQuote(
            cotacaoCompra=float("inf"),
            cotacaoVenda=float("inf"),
            dataHoraBoletimIso=NOW,
        )


@pytest.mark.asyncio
async def test_cache_hit_nao_consulta_banco_central() -> None:
    entry = CacheEntry(quote=quote(), synced_at=NOW - timedelta(minutes=5))
    upstream = CountingClient(quote())
    result = await PtaxService(MemoryCache(fresh=entry), upstream).get(NOW)  # type: ignore[arg-type]
    assert result.sucesso and upstream.calls == 0
    assert result.estadoDisponibilidade == "NORMAL"


@pytest.mark.asyncio
async def test_cache_miss_consulta_e_armazena() -> None:
    cache = MemoryCache()
    upstream = CountingClient(quote())
    result = await PtaxService(cache, upstream).get(NOW)  # type: ignore[arg-type]
    assert result.sucesso and upstream.calls == 1 and cache.fresh is not None


@pytest.mark.asyncio
async def test_cache_expirado_e_lista_vazia_servem_ultimo_valor() -> None:
    last = CacheEntry(quote=quote(2), synced_at=NOW - timedelta(days=2))
    upstream = CountingClient(None)
    result = await PtaxService(MemoryCache(last=last), upstream).get(NOW)  # type: ignore[arg-type]
    assert result.sucesso
    assert result.estadoDisponibilidade == "FONTE_INDISPONIVEL"
    assert result.estadoCotacao == "ULTIMO_FECHAMENTO_CONHECIDO"


@pytest.mark.asyncio
async def test_falha_redis_usa_fallback_local_configurado() -> None:
    cache = MemoryCache(shared=False)
    upstream = CountingClient(quote())
    result = await PtaxService(cache, upstream).get(NOW)  # type: ignore[arg-type]
    assert result.sucesso and upstream.calls == 1


@pytest.mark.asyncio
async def test_falha_upstream_sem_ultimo_valor_fica_indisponivel() -> None:
    upstream = CountingClient(error=httpx.ConnectError("offline"))
    result = await PtaxService(MemoryCache(), upstream).get(NOW)  # type: ignore[arg-type]
    assert not result.sucesso
    assert result.estadoDisponibilidade == "INDISPONIVEL"
    assert result.cotacaoCompra is None


@pytest.mark.asyncio
async def test_concorrencia_dispara_apenas_uma_consulta_upstream() -> None:
    cache = MemoryCache()
    upstream = CountingClient(quote(), delay=0.05)
    service = PtaxService(cache, upstream)  # type: ignore[arg-type]
    first, second = await asyncio.gather(service.get(NOW), service.get(NOW))
    assert first.sucesso and second.sucesso and upstream.calls == 1


def test_endpoint_nao_declara_dependencias_de_banco_tenant_ou_auth() -> None:
    source = inspect.getsource(get_public_ptax)
    assert "get_session" not in source
    assert "get_tenant" not in source
    assert "get_current_user" not in source
    assert "AsyncSession" not in source
