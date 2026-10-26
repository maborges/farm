# ruff: noqa: UP017
"""Testes unitários e de integração para o backend público de clima do DeepFarms Agro.

Cobre todos os 13 requisitos mandatórios da etapa DEEPFARMS-AGRO-FREE-01F-CLIMA-01B:
1. Endpoint público sem autenticação.
2. Validação de latitude e longitude.
3. Normalização de unidades (temperatura °C, vento km/h, chuva mm, umidade %).
4. Datas UTC e fuso local da localidade.
5. Payload com campos ausentes (sem valores fictícios).
6. Cache hit/miss e expiração.
7. Falha de Redis e degradação transparente.
8. Timeout de provedor.
9. Resposta desatualizada identificada (stale fallback).
10. Rejeição de provedor não configurado / não licenciado.
11. Ausência absoluta de acesso ao PostgreSQL corporativo.
12. Concorrência e proteção contra chamadas duplicadas (single-flight lock).
13. Proteção contra abuso e limites de consulta (Rate Limiting HTTP 429).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from public_clima.adapters import (
    OpenMeteoAdapter,
    OpenWeatherOneCallAdapter,
    ProviderAuthenticationError,
    ProviderLocationNotFoundError,
    ProviderQuotaExceededError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnconfiguredError,
    ProviderUnlicensedError,
    SyntheticFixtureAdapter,
    WeatherAPIAdapter,
)
from public_clima.cache import ClimaCache
from public_clima.catalog import MunicipalCatalog
from public_clima.contracts import ClimaPrevisaoResponse, CondicaoAtual
from public_clima.grid import GeoGridPolicy
from public_clima.router import get_clima_service, get_municipal_catalog
from public_clima.service import PublicClimaService


@pytest.fixture
def memory_cache() -> ClimaCache:
    """Fixture de cache configurado com single_worker_fallback sem Redis."""
    cache = ClimaCache("redis://localhost:6379/0", single_worker_fallback=True)
    cache.redis_ready = AsyncMock(return_value=False)
    return cache


@pytest.fixture
def fixture_service(memory_cache: ClimaCache) -> PublicClimaService:
    """Serviço configurado com adaptador sintético determinístico para testes locais."""
    provider = SyntheticFixtureAdapter(provider_id="FIXTURE_TESTE")
    grid = GeoGridPolicy(step_degrees=0.05)
    return PublicClimaService(
        cache=memory_cache,
        provider=provider,
        grid_policy=grid,
        ttl_seconds=1800,
    )


# 1. Endpoint público sem autenticação
def test_01_endpoint_publico_sem_autenticacao(fixture_service: PublicClimaService):
    app.dependency_overrides[get_clima_service] = lambda: fixture_service
    try:
        client = TestClient(app)
        # Nenhuma credencial, cookie ou header Authorization enviado
        resp = client.get("/api/v1/public/clima/previsao?lat=-23.5505&lon=-46.6333")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provedor"] == "FIXTURE_TESTE"
        assert data["latitude"] == -23.5505
        assert data["longitude"] == -46.6333
        assert "condicoesAtuais" in data
        assert data["statusOperacional"] == "NORMAL"
    finally:
        app.dependency_overrides.pop(get_clima_service, None)


# 2. Validação de latitude e longitude
@pytest.mark.parametrize(
    "lat,lon,expected_status",
    [
        (95.0, -46.0, 422),   # Latitude acima de 90
        (-95.0, -46.0, 422),  # Latitude abaixo de -90
        (-23.0, 185.0, 422),  # Longitude acima de 180
        (-23.0, -185.0, 422), # Longitude abaixo de -180
        ("invalido", -46.0, 422), # Tipo inválido
        (-23.421, -51.933, 200),  # Coordenada válida de Maringá/PR
    ],
)
def test_02_validacao_latitude_longitude(
    fixture_service: PublicClimaService, lat: Any, lon: Any, expected_status: int
):
    app.dependency_overrides[get_clima_service] = lambda: fixture_service
    try:
        client = TestClient(app)
        resp = client.get(f"/api/v1/public/clima/previsao?lat={lat}&lon={lon}")
        assert resp.status_code == expected_status
    finally:
        app.dependency_overrides.pop(get_clima_service, None)


# 3. Normalização de unidades
@pytest.mark.asyncio
async def test_03_normalizacao_unidades(fixture_service: PublicClimaService):
    resp = await fixture_service.get_previsao(-23.5505, -46.6333)

    # Temperatura em °C
    assert resp.temperaturaAtualC is not None
    assert isinstance(resp.temperaturaAtualC, int | float)
    assert -50.0 <= resp.temperaturaAtualC <= 60.0

    # Vento em km/h
    assert resp.ventoVelocidadeKmH is not None
    assert resp.ventoVelocidadeKmH >= 0.0

    # Umidade em % (0 a 100)
    assert resp.umidadeRelativaPct is not None
    assert 0 <= resp.umidadeRelativaPct <= 100

    # Precipitação em mm
    assert resp.precipitacaoMm is not None
    assert resp.precipitacaoMm >= 0.0


# 4. Datas UTC e fuso local
@pytest.mark.asyncio
async def test_04_datas_utc_e_fuso_local(fixture_service: PublicClimaService):
    resp = await fixture_service.get_previsao(-23.5505, -46.6333)

    # Timestamps com fuso horário UTC válido
    assert resp.horarioReferenciaIso.tzinfo is not None
    assert resp.obtidoEmIso.tzinfo is not None
    assert resp.validoAteIso.tzinfo is not None

    # Fuso local documentado
    assert resp.fusoHorario == "America/Sao_Paulo"

    # Previsão horária de 24 horas consecutivas
    assert len(resp.previsaoHoraria) == 24
    for item in resp.previsaoHoraria:
        assert "T" in item.horaIso

    # Previsão diária de 7 dias com nomes dos dias em português
    assert len(resp.previsaoDiaria) == 7
    for item in resp.previsaoDiaria:
        assert item.diaSemana in [
            "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sábado", "domingo"
        ]


# 5. Payload com campos ausentes sem valores fictícios
@pytest.mark.asyncio
async def test_05_payload_com_campos_ausentes(memory_cache: ClimaCache):
    class IncompleteProvider:
        provider_id = "PROVEDOR_MINIMO"
        is_licensed = True

        async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
            now = datetime.now(timezone.utc)
            return ClimaPrevisaoResponse(
                latitude=lat,
                longitude=lon,
                latitudeGrid=lat,
                longitudeGrid=lon,
                fusoHorario="America/Sao_Paulo",
                provedor="PROVEDOR_MINIMO",
                licencaFonte="Teste sem campos opcionais",
                tipoDado="OBSERVADO",
                temperaturaAtualC=22.0,
                sensacaoTermicaC=None,  # Ausente intencionalmente
                umidadeRelativaPct=None,  # Ausente intencionalmente
                ventoVelocidadeKmH=None,  # Ausente intencionalmente
                ventoRajadasKmH=None,  # Ausente intencionalmente
                precipitacaoMm=None,  # Ausente intencionalmente
                probabilidadeChuvaPct=None,  # Ausente intencionalmente
                condicoesAtuais=CondicaoAtual(temperaturaC=22.0),
                previsaoHoraria=[],
                previsaoDiaria=[],
                horarioReferenciaIso=now,
                obtidoEmIso=now,
                validoAteIso=now,
            )

    service = PublicClimaService(cache=memory_cache, provider=IncompleteProvider())
    resp = await service.get_previsao(-23.5505, -46.6333)

    assert resp.temperaturaAtualC == 22.0
    assert resp.sensacaoTermicaC is None
    assert resp.umidadeRelativaPct is None
    assert resp.ventoRajadasKmH is None
    assert resp.precipitacaoMm is None


# 6. Cache hit, miss e expiração
@pytest.mark.asyncio
async def test_06_cache_hit_miss_e_expiracao(memory_cache: ClimaCache):
    chamadas_provider = 0

    class CountingProvider:
        provider_id = "COUNTING"
        is_licensed = True

        async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
            nonlocal chamadas_provider
            chamadas_provider += 1
            now = datetime.now(timezone.utc)
            return ClimaPrevisaoResponse(
                latitude=lat,
                longitude=lon,
                latitudeGrid=lat,
                longitudeGrid=lon,
                fusoHorario="UTC",
                provedor="COUNTING",
                licencaFonte="Teste",
                tipoDado="PREVISTO",
                temperaturaAtualC=25.0,
                horarioReferenciaIso=now,
                obtidoEmIso=now,
                validoAteIso=now,
            )

    service = PublicClimaService(cache=memory_cache, provider=CountingProvider(), ttl_seconds=2)

    # 1ª Consulta: Cache MISS
    resp1 = await service.get_previsao(-23.55, -46.63)
    assert resp1.emCache is False
    assert chamadas_provider == 1

    # 2ª Consulta imediata: Cache HIT
    resp2 = await service.get_previsao(-23.55, -46.63)
    assert resp2.emCache is True
    assert chamadas_provider == 1  # Não deve chamar o provider de novo

    # Simula passagem de tempo do TTL no cache local
    key = service.grid_policy.cache_key(-23.55, -46.63)
    memory_cache.local_fresh[key] = (memory_cache.local_fresh[key][0], 0.0)

    # 3ª Consulta pós-expiração: Novo MISS
    resp3 = await service.get_previsao(-23.55, -46.63)
    assert resp3.emCache is False
    assert chamadas_provider == 2


# 7. Falha de Redis com degradação transparente
@pytest.mark.asyncio
async def test_07_falha_redis_degradacao_transparente():
    failing_redis_cache = ClimaCache("redis://localhost:6379/0", single_worker_fallback=True)
    # Simula falha total do Redis
    failing_redis_cache.redis_ready = AsyncMock(return_value=False)
    failing_redis_cache.redis.get = AsyncMock(side_effect=ConnectionError("Redis offline"))
    failing_redis_cache.redis.set = AsyncMock(side_effect=ConnectionError("Redis offline"))

    service = PublicClimaService(
        cache=failing_redis_cache,
        provider=SyntheticFixtureAdapter(),
        ttl_seconds=300,
    )

    # Deve funcionar perfeitamente com degradação transparente em memória
    resp = await service.get_previsao(-23.55, -46.63)
    assert resp.temperaturaAtualC is not None

    # E o cache de memória deve registrar a entrada normalmente
    key = service.grid_policy.cache_key(-23.55, -46.63)
    assert key in failing_redis_cache.local_fresh


# 8. Timeout de provedor sem cache prévio
@pytest.mark.asyncio
async def test_08_timeout_provedor_sem_cache(memory_cache: ClimaCache):
    timing_out_provider = SyntheticFixtureAdapter(
        simular_falha=ProviderTimeoutError("Tempo limite excedido")
    )
    service = PublicClimaService(cache=memory_cache, provider=timing_out_provider)

    with pytest.raises(ProviderTimeoutError):
        await service.get_previsao(-23.55, -46.63)


# 9. Resposta desatualizada identificada (stale fallback)
@pytest.mark.asyncio
async def test_09_resposta_desatualizada_identificada(memory_cache: ClimaCache):
    deve_falhar = False

    class FlakyProvider:
        provider_id = "FLAKY"
        is_licensed = True

        async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
            if deve_falhar:
                raise ProviderUnavailableError("Servidor upstream fora do ar")
            now = datetime.now(timezone.utc)
            return ClimaPrevisaoResponse(
                latitude=lat,
                longitude=lon,
                latitudeGrid=lat,
                longitudeGrid=lon,
                fusoHorario="UTC",
                provedor="FLAKY",
                licencaFonte="Teste",
                tipoDado="PREVISTO",
                temperaturaAtualC=28.0,
                horarioReferenciaIso=now,
                obtidoEmIso=now,
                validoAteIso=now,
            )

    service = PublicClimaService(cache=memory_cache, provider=FlakyProvider(), ttl_seconds=1)

    # 1ª Consulta bem-sucedida (grava fresh e last)
    resp1 = await service.get_previsao(-23.55, -46.63)
    assert resp1.statusOperacional == "NORMAL"
    assert resp1.desatualizado is False

    # Força expiração do fresh cache
    key = service.grid_policy.cache_key(-23.55, -46.63)
    memory_cache.local_fresh.pop(key, None)

    # Agora o provedor começa a falhar
    deve_falhar = True

    # 2ª Consulta: Deve retornar os dados do `last` marcados como DESATUALIZADO
    resp2 = await service.get_previsao(-23.55, -46.63)
    assert resp2.desatualizado is True
    assert resp2.statusOperacional == "DESATUALIZADO"
    assert resp2.temperaturaAtualC == 28.0


# 10. Rejeição de provedor não configurado ou não licenciado
def test_10_rejeicao_provedor_nao_licenciado(memory_cache: ClimaCache):
    unlicensed_adapter = OpenMeteoAdapter(
        is_licensed=False,
        allow_unlicensed_public=False,
    )
    service = PublicClimaService(cache=memory_cache, provider=unlicensed_adapter)
    app.dependency_overrides[get_clima_service] = lambda: service

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/public/clima/previsao?lat=-23.55&lon=-46.63")
        assert resp.status_code == 503
        assert "não licenciado para produção" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_clima_service, None)


# 11. Ausência absoluta de acesso ao PostgreSQL comercial
def test_11_ausencia_absoluta_acesso_postgresql(fixture_service: PublicClimaService):
    app.dependency_overrides[get_clima_service] = lambda: fixture_service
    try:
        with patch("core.database.async_session_maker") as mock_session_maker:
            client = TestClient(app)
            resp = client.get("/api/v1/public/clima/previsao?lat=-23.55&lon=-46.63")
            assert resp.status_code == 200
            # async_session_maker NUNCA pode ser chamado pelo endpoint público
            mock_session_maker.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_clima_service, None)


# 12. Concorrência e proteção contra chamadas duplicadas (Single-flight lock)
@pytest.mark.asyncio
async def test_12_concorrencia_e_protecao_chamadas_duplicadas(memory_cache: ClimaCache):
    total_requisicoes_externas = 0

    class SlowProvider:
        provider_id = "SLOW"
        is_licensed = True

        async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
            nonlocal total_requisicoes_externas
            total_requisicoes_externas += 1
            await asyncio.sleep(0.3)  # Simula latência de rede
            now = datetime.now(timezone.utc)
            return ClimaPrevisaoResponse(
                latitude=lat,
                longitude=lon,
                latitudeGrid=lat,
                longitudeGrid=lon,
                fusoHorario="UTC",
                provedor="SLOW",
                licencaFonte="Teste",
                tipoDado="PREVISTO",
                temperaturaAtualC=21.0,
                horarioReferenciaIso=now,
                obtidoEmIso=now,
                validoAteIso=now,
            )

    service = PublicClimaService(cache=memory_cache, provider=SlowProvider(), ttl_seconds=60)

    # 10 chamadas concorrentes para as mesmas coordenadas
    tarefas = [service.get_previsao(-23.5501, -46.6301) for _ in range(10)]
    respostas = await asyncio.gather(*tarefas)

    # Todas devem receber os mesmos dados
    for r in respostas:
        assert r.temperaturaAtualC == 21.0

    # O provedor externo deve ter sido chamado EXATAMENTE UMA VEZ
    assert total_requisicoes_externas == 1


# 13. Proteção contra abuso e limites de consulta (Rate Limiting HTTP 429)
def test_13_rate_limiting_abuso(fixture_service: PublicClimaService):
    app.dependency_overrides[get_clima_service] = lambda: fixture_service
    try:
        client = TestClient(app)

        # Efetua 60 requisições (dentro do limite)
        for _ in range(60):
            r = client.get("/api/v1/public/clima/previsao?lat=-23.55&lon=-46.63")
            assert r.status_code == 200

        # A 61ª requisição deve ser bloqueada com 429
        bloqueado = client.get("/api/v1/public/clima/previsao?lat=-23.55&lon=-46.63")
        assert bloqueado.status_code == 429
        assert "Limite de consultas de clima excedido" in bloqueado.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_clima_service, None)


# 14. Busca de municípios com e sem acentos
def test_14_busca_municipios_com_e_sem_acentos():
    client = TestClient(app)

    # Busca com acentuação
    r1 = client.get("/api/v1/public/clima/municipios?q=São Paulo")
    assert r1.status_code == 200
    dados1 = r1.json()
    assert dados1["sucesso"] is True
    assert dados1["total"] >= 1
    assert dados1["itens"][0]["nome"] == "São Paulo"
    assert dados1["itens"][0]["uf"] == "SP"
    assert dados1["itens"][0]["codigoIbge"] == 3550308
    assert -24.0 <= dados1["itens"][0]["latitude"] <= -23.0
    assert -47.0 <= dados1["itens"][0]["longitude"] <= -46.0

    # Busca sem acentuação (mesmo resultado exato em primeiro)
    r2 = client.get("/api/v1/public/clima/municipios?q=sao paulo")
    assert r2.status_code == 200
    dados2 = r2.json()
    assert dados2["itens"][0]["codigoIbge"] == 3550308

    # Busca com termo acentuado (Goiânia vs goiania)
    r3 = client.get("/api/v1/public/clima/municipios?q=goiania")
    assert r3.status_code == 200
    assert r3.json()["itens"][0]["nome"] == "Goiânia"
    assert r3.json()["itens"][0]["uf"] == "GO"


# 15. Municípios homônimos
def test_15_municipios_homonimos():
    client = TestClient(app)

    # "Bom Jesus" existe em múltiplos estados (PB, PI, RN, RS, SC)
    r = client.get("/api/v1/public/clima/municipios?q=Bom Jesus")
    assert r.status_code == 200
    dados = r.json()
    assert dados["total"] >= 5

    # Todos os "Bom Jesus" retornados têm código IBGE e UF distintos
    nomes_ufs = [(m["nome"], m["uf"]) for m in dados["itens"] if m["nome"] == "Bom Jesus"]
    assert len(nomes_ufs) >= 5
    ufs_encontradas = {uf for _, uf in nomes_ufs}
    assert {"RS", "SC", "PI"}.issubset(ufs_encontradas)

    codigos = [m["codigoIbge"] for m in dados["itens"]]
    assert len(codigos) == len(set(codigos))  # Sem duplicatas


# 16. Filtro por UF e paginação
def test_16_filtro_por_uf_e_paginacao():
    client = TestClient(app)

    # Lista municípios do Paraná (PR)
    r = client.get("/api/v1/public/clima/municipios?uf=PR&limit=15&offset=0")
    assert r.status_code == 200
    dados = r.json()
    assert dados["sucesso"] is True
    assert dados["total"] == 399  # PR tem exatamente 399 municípios no IBGE
    assert len(dados["itens"]) == 15
    for item in dados["itens"]:
        assert item["uf"] == "PR"

    # Próxima página
    r_pag2 = client.get("/api/v1/public/clima/municipios?uf=PR&limit=15&offset=15")
    assert r_pag2.status_code == 200
    dados2 = r_pag2.json()
    assert len(dados2["itens"]) == 15
    assert dados2["itens"][0]["codigoIbge"] != dados["itens"][0]["codigoIbge"]


# 17. Rejeição de UF inválida
def test_17_rejeicao_uf_invalida():
    client = TestClient(app)
    r = client.get("/api/v1/public/clima/municipios?uf=XX")
    assert r.status_code == 400
    assert "UF 'XX' inválida" in r.json()["detail"]


# 18. Rejeição de consulta com critérios insuficientes
def test_18_rejeicao_criterios_insuficientes():
    client = TestClient(app)

    # Sem parâmetros
    r1 = client.get("/api/v1/public/clima/municipios")
    assert r1.status_code == 400
    assert "Informe pelo menos 2 caracteres" in r1.json()["detail"]

    # Com query de apenas 1 caractere e sem UF
    r2 = client.get("/api/v1/public/clima/municipios?q=a")
    assert r2.status_code == 400
    assert "Informe pelo menos 2 caracteres" in r2.json()["detail"]


# 19. Tratamento de catálogo indisponível
def test_19_catalogo_indisponivel(tmp_path):
    client = TestClient(app)
    inexistente = tmp_path / "nao_existe.json"

    class BrokenCatalog(MunicipalCatalog):
        def __init__(self):
            super().__init__(data_path=inexistente)

    app.dependency_overrides[get_municipal_catalog] = lambda: BrokenCatalog()
    try:
        r = client.get("/api/v1/public/clima/municipios?q=Maringa")
        assert r.status_code == 503
        assert "Catálogo territorial ausente" in r.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_municipal_catalog, None)


# 20. Ausência absoluta de acesso ao PostgreSQL comercial na busca territorial
def test_20_busca_municipios_sem_acesso_postgresql():
    client = TestClient(app)

    with patch("core.database.async_session_maker") as mock_session_maker:
        r = client.get("/api/v1/public/clima/municipios?q=Londrina&uf=PR")
        assert r.status_code == 200
        assert r.json()["itens"][0]["nome"] == "Londrina"
        # Garante que zero sessões foram criadas
        mock_session_maker.assert_not_called()


# 21. OpenWeatherOneCallAdapter rejeita execução quando não licenciado
@pytest.mark.asyncio
async def test_21_openweather_adapter_bloqueado_sem_licenca():
    adapter = OpenWeatherOneCallAdapter(
        api_key="chave_falsa_teste",
        is_licensed=False,
        allow_unlicensed_public=False,
    )
    with pytest.raises(ProviderUnlicensedError) as exc_info:
        await adapter.fetch_forecast(-23.55, -46.63)
    assert "não licenciado para uso público" in str(exc_info.value)


# 22. OpenWeatherOneCallAdapter rejeita execução quando chave não configurada
@pytest.mark.asyncio
async def test_22_openweather_adapter_bloqueado_sem_chave():
    adapter = OpenWeatherOneCallAdapter(
        api_key=None,
        is_licensed=True,
        allow_unlicensed_public=False,
    )
    with pytest.raises(ProviderUnlicensedError) as exc_info:
        await adapter.fetch_forecast(-23.55, -46.63)
    assert "Chave de API do OpenWeather (One Call 3.0) não configurada" in str(exc_info.value)


# 23. OpenWeatherOneCallAdapter normaliza payload One Call 3.0 para o contrato agrometeorológico
@pytest.mark.asyncio
async def test_23_openweather_adapter_normalizacao_onecall():
    mock_payload = {
        "lat": -23.55,
        "lon": -46.63,
        "timezone": "America/Sao_Paulo",
        "current": {
            "dt": 1761168000,
            "temp": 26.4,
            "feels_like": 27.1,
            "humidity": 65,
            "wind_speed": 4.5,  # 4.5 m/s = 16.2 km/h
            "wind_deg": 120,
            "wind_gust": 7.0,   # 7.0 m/s = 25.2 km/h
            "rain": {"1h": 0.5},
            "weather": [
                {
                    "id": 801,
                    "main": "Clouds",
                    "description": "poucas nuvens",
                    "icon": "02d",
                }
            ],
        },
        "hourly": [
            {
                "dt": 1761168000 + i * 3600,
                "temp": 24.0 + (i % 5),
                "feels_like": 25.0 + (i % 5),
                "humidity": 60 + (i % 20),
                "wind_speed": 3.0,  # 10.8 km/h
                "wind_deg": 90,
                "wind_gust": 5.0,   # 18.0 km/h
                "pop": 0.25,        # 25%
                "rain": {"1h": 0.0},
                "weather": [{"icon": "02d", "description": "poucas nuvens"}],
            }
            for i in range(24)
        ],
        "daily": [
            {
                "dt": 1761168000 + d * 86400,
                "temp": {"min": 18.0 + d, "max": 28.0 + d},
                "wind_speed": 4.0,  # 14.4 km/h
                "pop": 0.40,        # 40%
                "rain": 2.5 if d == 1 else 0.0,
                "weather": [{"icon": "10d" if d == 1 else "01d", "description": "chuva leve" if d == 1 else "céu limpo"}],
            }
            for d in range(7)
        ],
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_payload
    mock_resp.raise_for_status.return_value = None
    mock_client.get.return_value = mock_resp

    adapter = OpenWeatherOneCallAdapter(
        api_key="chave_autorizada_teste",
        is_licensed=True,
        client=mock_client,
    )

    resultado = await adapter.fetch_forecast(-23.55, -46.63)

    assert resultado.provedor == "OPENWEATHER"
    assert resultado.dadosSinteticos is False
    assert resultado.temperaturaAtualC == 26.4
    assert resultado.sensacaoTermicaC == 27.1
    assert resultado.umidadeRelativaPct == 65
    assert resultado.ventoVelocidadeKmH == 16.2  # 4.5 * 3.6
    assert resultado.ventoDirecaoGraus == 120
    assert resultado.ventoRajadasKmH == 25.2      # 7.0 * 3.6
    assert resultado.precipitacaoMm == 0.5
    assert resultado.condicaoDescricao == "Poucas nuvens"
    assert resultado.condicaoIcone == "CloudSun"

    # Horária
    assert len(resultado.previsaoHoraria) == 24
    assert resultado.previsaoHoraria[0].probabilidadeChuvaPct == 25
    assert resultado.previsaoHoraria[0].ventoKmH == 10.8

    # Diária
    assert len(resultado.previsaoDiaria) == 7
    assert resultado.previsaoDiaria[0].probabilidadeChuvaPct == 40
    assert resultado.previsaoDiaria[1].condicaoIcone == "CloudRain"
    assert resultado.previsaoDiaria[1].precipitacaoMm == 2.5


# ============================================================================
# TESTES WEATHERAPI — PILOTO CONTROLADO (DEEPFARMS-AGRO-FREE-01F-CLIMA-01F)
# ============================================================================


@pytest.mark.asyncio
async def test_weatherapi_unlicensed_or_disabled():
    """Garante que a WeatherAPI rejeita execução se desabilitada ou sem chave."""
    adapter_disabled = WeatherAPIAdapter(api_key="alguma_chave", is_enabled=False)
    with pytest.raises(ProviderUnlicensedError, match="não está habilitado"):
        await adapter_disabled.fetch_forecast(-23.55, -46.63)

    adapter_no_key = WeatherAPIAdapter(api_key="", is_enabled=True)
    with pytest.raises(ProviderUnlicensedError, match="credencial não informada"):
        await adapter_no_key.fetch_forecast(-23.55, -46.63)


def test_weatherapi_credentials_protection():
    """Garante que a API Key NUNCA é vazada via __repr__ ou __str__."""
    secret = "wapi_secret_key_prod_abc123xyz"
    adapter = WeatherAPIAdapter(api_key=secret, is_enabled=True, max_days=3)
    assert secret not in repr(adapter)
    assert secret not in str(adapter)
    assert "wapi_secret" not in repr(adapter)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "err_code,status_code,expected_exc",
    [
        (1002, 401, ProviderUnconfiguredError),
        (1005, 400, ProviderAuthenticationError),
        (1006, 400, ProviderLocationNotFoundError),
        (2006, 401, ProviderAuthenticationError),
        (2007, 403, ProviderQuotaExceededError),
        (2008, 403, ProviderAuthenticationError),
        (2009, 403, ProviderUnlicensedError),
        (9999, 500, ProviderUnavailableError),
    ],
)
async def test_weatherapi_error_mapping(err_code: int, status_code: int, expected_exc: type[Exception]):
    """Valida o mapeamento estrito de todos os códigos de erro documentados da WeatherAPI."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {
        "error": {"code": err_code, "message": f"Erro simulado {err_code}"}
    }
    mock_client.get.return_value = mock_resp

    adapter = WeatherAPIAdapter(api_key="chave_valida", is_enabled=True, client=mock_client)
    with pytest.raises(expected_exc):
        await adapter.fetch_forecast(-23.55, -46.63)


@pytest.mark.asyncio
async def test_weatherapi_normalization_free_plan_3_days():
    """Valida a normalização completa do plano Free (3 dias, sem preenchimento artificial)."""
    # 3 dias de dados meteorológicos reais
    base_epoch = 1792699200  # 2026-10-22 20:00:00 UTC
    mock_payload = {
        "location": {
            "name": "Ribeirão Preto",
            "region": "São Paulo",
            "country": "Brazil",
            "lat": -21.17,
            "lon": -47.81,
            "tz_id": "America/Sao_Paulo",
            "localtime_epoch": base_epoch,
            "localtime": "2026-10-22 17:00",
        },
        "current": {
            "last_updated_epoch": base_epoch,
            "last_updated": "2026-10-22 17:00",
            "temp_c": 28.5,
            "is_day": 1,
            "condition": {"text": "Ensolarado", "icon": "//cdn.weatherapi.com/...", "code": 1000},
            "wind_kph": 18.0,
            "wind_degree": 90,
            "precip_mm": 0.0,
            "humidity": 45,
            "feelslike_c": 29.8,
            "gust_kph": 27.5,
        },
        "forecast": {
            "forecastday": [
                {
                    "date": f"2026-10-{22+d:02d}",
                    "date_epoch": base_epoch + d * 86400,
                    "day": {
                        "maxtemp_c": 32.0 + d,
                        "mintemp_c": 20.0 + d,
                        "maxwind_kph": 25.0,
                        "totalprecip_mm": 5.0 if d == 1 else 0.0,
                        "daily_chance_of_rain": 60 if d == 1 else 10,
                        "condition": {"text": "Chuva passageira" if d == 1 else "Sol", "code": 1063 if d == 1 else 1000},
                    },
                    "hour": [
                        {
                            "time_epoch": base_epoch + (d * 24 + h) * 3600,
                            "time": f"2026-10-{22+d:02d} {h:02d}:00",
                            "temp_c": 22.0 + (h % 10),
                            "feelslike_c": 23.0 + (h % 10),
                            "humidity": 50 + (h % 20),
                            "wind_kph": 12.0,
                            "wind_degree": 100,
                            "gust_kph": 18.0,
                            "precip_mm": 0.5 if h == 14 else 0.0,
                            "chance_of_rain": 40 if h == 14 else 5,
                            "is_day": 1 if 6 <= h <= 18 else 0,
                            "condition": {"text": "Sol", "code": 1000},
                        }
                        for h in range(24)
                    ],
                }
                for d in range(3)  # Exatamente 3 dias no plano Free
            ]
        },
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_client.get.return_value = mock_resp

    adapter = WeatherAPIAdapter(
        api_key="chave_teste_homologacao",
        is_enabled=True,
        max_days=3,
        client=mock_client,
    )

    resultado = await adapter.fetch_forecast(-21.17, -47.81)

    assert resultado.provedor == "WEATHERAPI"
    assert resultado.dadosSinteticos is False
    assert "WeatherAPI.com" in resultado.licencaFonte
    assert resultado.fusoHorario == "America/Sao_Paulo"

    # Condições atuais
    assert resultado.temperaturaAtualC == 28.5
    assert resultado.sensacaoTermicaC == 29.8
    assert resultado.umidadeRelativaPct == 45
    assert resultado.ventoVelocidadeKmH == 18.0
    assert resultado.ventoDirecaoGraus == 90
    assert resultado.ventoRajadasKmH == 27.5
    assert resultado.precipitacaoMm == 0.0
    assert resultado.condicaoIcone == "Sun"

    # Previsão Diária — rigorosamente 3 dias (sem preenchimento artificial para 7)
    assert len(resultado.previsaoDiaria) == 3
    assert resultado.previsaoDiaria[0].dataIso == "2026-10-22"
    assert resultado.previsaoDiaria[1].precipitacaoMm == 5.0
    assert resultado.previsaoDiaria[1].probabilidadeChuvaPct == 60
    assert resultado.previsaoDiaria[1].condicaoIcone == "CloudRain"

    # Previsão Horária — 24 horas contínuas
    assert len(resultado.previsaoHoraria) == 24


@pytest.mark.asyncio
async def test_weatherapi_normalization_starter_plan_7_days():
    """Valida a normalização do plano Starter com 7 dias de previsão diária."""
    base_epoch = 1792699200
    mock_payload = {
        "location": {"tz_id": "America/Cuiaba", "localtime_epoch": base_epoch},
        "current": {"temp_c": 35.0, "humidity": 30, "wind_kph": 10.0, "is_day": 1, "condition": {"code": 1000}},
        "forecast": {
            "forecastday": [
                {
                    "date": f"2026-10-{22+d:02d}",
                    "day": {"maxtemp_c": 36.0, "mintemp_c": 22.0, "daily_chance_of_rain": 0, "condition": {"code": 1000}},
                    "hour": [
                        {
                            "time_epoch": base_epoch + (d * 24 + h) * 3600,
                            "temp_c": 30.0,
                            "condition": {"code": 1000},
                        }
                        for h in range(24)
                    ],
                }
                for d in range(7)  # 7 dias no plano Starter
            ]
        },
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_client.get.return_value = mock_resp

    adapter = WeatherAPIAdapter(
        api_key="chave_starter_autorizada",
        is_enabled=True,
        max_days=7,
        client=mock_client,
    )

    resultado = await adapter.fetch_forecast(-15.60, -56.09)
    assert len(resultado.previsaoDiaria) == 7
    assert len(resultado.previsaoHoraria) == 24


@pytest.mark.asyncio
async def test_weatherapi_rolling_24h_crossing_midnight():
    """Valida que a janela de 24 horas ultrapassa a meia-noite contínua e ordenadamente."""
    # Referência: 20:00 (hora local/UTC) do Dia 0
    dia0_20h = 1792700000 - (1792700000 % 3600)  # múltiplo de hora
    mock_payload = {
        "location": {"tz_id": "America/Sao_Paulo", "localtime_epoch": dia0_20h},
        "current": {"temp_c": 21.0, "is_day": 0, "condition": {"code": 1000}},
        "forecast": {
            "forecastday": [
                {
                    "date": "2026-10-22",
                    "day": {"maxtemp_c": 28.0, "mintemp_c": 19.0, "daily_chance_of_rain": 10, "condition": {"code": 1000}},
                    "hour": [
                        {
                            "time_epoch": dia0_20h - 20 * 3600 + h * 3600,  # 00:00 a 23:00 do dia 0
                            "time": f"2026-10-22 {h:02d}:00",
                            "temp_c": 20.0 + h,
                            "condition": {"code": 1000},
                        }
                        for h in range(24)
                    ],
                },
                {
                    "date": "2026-10-23",
                    "day": {"maxtemp_c": 30.0, "mintemp_c": 20.0, "daily_chance_of_rain": 20, "condition": {"code": 1000}},
                    "hour": [
                        {
                            "time_epoch": dia0_20h + 4 * 3600 + h * 3600,  # 00:00 a 23:00 do dia 1
                            "time": f"2026-10-23 {h:02d}:00",
                            "temp_c": 18.0 + h,
                            "condition": {"code": 1000},
                        }
                        for h in range(24)
                    ],
                },
            ]
        },
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_client.get.return_value = mock_resp

    adapter = WeatherAPIAdapter(
        api_key="chave_teste",
        is_enabled=True,
        max_days=2,
        client=mock_client,
    )

    resultado = await adapter.fetch_forecast(-23.55, -46.63)
    assert len(resultado.previsaoHoraria) == 24

    # Primeira hora deve ser 20:00 do dia 0
    assert "2026-10-22" in resultado.previsaoHoraria[0].horaIso
    # Última hora deve ser 19:00 do dia 1 (atravessando meia-noite perfeitamente)
    assert "2026-10-23" in resultado.previsaoHoraria[-1].horaIso


@pytest.mark.asyncio
async def test_clima_cache_telemetry_and_quota(memory_cache: ClimaCache):
    """Valida o registro de métricas operacionais e controle de cota na ClimaCache."""
    # Testar hit e miss
    await memory_cache.record_cache_hit("WEATHERAPI", shared=False)
    await memory_cache.record_cache_hit("WEATHERAPI", shared=False)
    await memory_cache.record_cache_miss("WEATHERAPI", shared=False)
    await memory_cache.record_error("WEATHERAPI", "timeout", shared=False)

    # Testar upstream e cota
    call_1 = await memory_cache.record_upstream_call("WEATHERAPI", shared=False)
    assert call_1 == 1

    # Limite de 5 chamadas
    assert await memory_cache.check_monthly_quota("WEATHERAPI", limit=5, shared=False) is True

    for _ in range(4):
        await memory_cache.record_upstream_call("WEATHERAPI", shared=False)

    # Agora acumulou 5 chamadas -> com limite 5, deve retornar False (esgotado)
    assert await memory_cache.check_monthly_quota("WEATHERAPI", limit=5, shared=False) is False

    # Diagnóstico sanitizado
    metrics = await memory_cache.get_metrics("WEATHERAPI", shared=False)
    assert metrics["upstream_calls_month"] == 5
    assert metrics["cache_hits"] == 2
    assert metrics["cache_misses"] == 1
    assert metrics["timeouts"] == 1


@pytest.mark.asyncio
async def test_clima_service_monthly_quota_enforcement(memory_cache: ClimaCache):
    """Garante que o serviço lança ProviderQuotaExceededError quando a cota interna é atingida."""
    provider = SyntheticFixtureAdapter(provider_id="WEATHERAPI")
    service = PublicClimaService(
        cache=memory_cache,
        provider=provider,
        monthly_quota_limit=2,  # Limite de apenas 2 chamadas
    )

    # 1ª chamada -> consome 1
    resp1 = await service.get_previsao(-23.55, -46.63)
    assert resp1.emCache is False

    # 2ª chamada para outra coordenada -> consome 2
    resp2 = await service.get_previsao(-22.00, -47.00)
    assert resp2.emCache is False

    # 3ª chamada para terceira coordenada -> deve exceder a cota e lançar ProviderQuotaExceededError
    with pytest.raises(ProviderQuotaExceededError, match="esgotada"):
        await service.get_previsao(-21.00, -48.00)


def test_fastapi_weatherapi_quota_exceeded_http_503(memory_cache: ClimaCache):
    """Valida que o endpoint HTTP retorna 503 amigável quando a cota da WeatherAPI é excedida."""
    failing_provider = SyntheticFixtureAdapter(
        provider_id="WEATHERAPI",
        simular_falha=ProviderQuotaExceededError("Franquia excedida"),
    )
    test_service = PublicClimaService(
        cache=memory_cache,
        provider=failing_provider,
    )
    app.dependency_overrides[get_clima_service] = lambda: test_service
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/public/clima/previsao?lat=-23.55&lon=-46.63")
        assert resp.status_code == 503
        data = resp.json()
        assert "franquia de consultas excedida" in data["detail"].lower()
        # Sem vazamento de segredos
        assert "key" not in data["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_clima_service, None)


