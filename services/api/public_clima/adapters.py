# ruff: noqa: UP017
"""Adaptadores e contratos para provedores meteorológicos externos e fixtures."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any, Protocol, runtime_checkable

import httpx
from loguru import logger

from core.config import settings

from .contracts import (
    ClimaPrevisaoResponse,
    CondicaoAtual,
    PrevisaoDiariaItem,
    PrevisaoHorariaItem,
)

DIAS_SEMANA_PT = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]

WMO_INTERPRETATION: dict[int, tuple[str, str]] = {
    0: ("Céu limpo", "Sun"),
    1: ("Predomínio de sol", "Sun"),
    2: ("Parcialmente nublado", "CloudSun"),
    3: ("Nublado", "Cloud"),
    45: ("Nevoeiro", "CloudFog"),
    48: ("Nevoeiro com geada", "CloudFog"),
    51: ("Garoa leve", "CloudDrizzle"),
    53: ("Garoa moderada", "CloudDrizzle"),
    55: ("Garoa densa", "CloudDrizzle"),
    56: ("Garoa congelante leve", "CloudSnow"),
    57: ("Garoa congelante densa", "CloudSnow"),
    61: ("Chuva fraca", "CloudRain"),
    63: ("Chuva moderada", "CloudRain"),
    65: ("Chuva forte", "CloudRain"),
    66: ("Chuva congelante leve", "CloudSnow"),
    67: ("Chuva congelante forte", "CloudSnow"),
    71: ("Queda de neve leve", "CloudSnow"),
    73: ("Queda de neve moderada", "CloudSnow"),
    75: ("Queda de neve forte", "CloudSnow"),
    77: ("Grãos de neve", "CloudSnow"),
    80: ("Pancadas de chuva fracas", "CloudRain"),
    81: ("Pancadas de chuva moderadas", "CloudRain"),
    82: ("Pancadas de chuva violentas", "CloudRain"),
    85: ("Pancadas de neve leves", "CloudSnow"),
    86: ("Pancadas de neve pesadas", "CloudSnow"),
    95: ("Tempestade", "CloudLightning"),
    96: ("Tempestade com granizo leve", "CloudLightning"),
    99: ("Tempestade com granizo pesado", "CloudLightning"),
}


class ProviderError(Exception):
    """Exceção base de falha de provedor meteorológico."""


class ProviderUnconfiguredError(ProviderError):
    """Lançada quando nenhum provedor válido está ativo."""


class ProviderUnlicensedError(ProviderError):
    """Lançada quando o provedor requer licença comercial que não está habilitada."""


class ProviderTimeoutError(ProviderError):
    """Lançada quando a comunicação com o provedor atinge tempo limite."""


class ProviderUnavailableError(ProviderError):
    """Lançada quando o serviço do provedor está fora do ar."""


class ProviderAuthenticationError(ProviderError):
    """Lançada quando a chave de API é inválida ou foi desabilitada."""


class ProviderQuotaExceededError(ProviderError):
    """Lançada quando a franquia mensal de chamadas foi esgotada."""


class ProviderLocationNotFoundError(ProviderError):
    """Lançada quando as coordenadas ou localização não foram encontradas."""


@runtime_checkable
class WeatherProvider(Protocol):
    """Protocolo canônico que todo adaptador meteorológico deve implementar."""

    provider_id: str
    is_licensed: bool

    async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
        """Busca a previsão meteorológica completa para as coordenadas indicadas."""
        ...


class OpenMeteoAdapter:
    """Adaptador para a API do Open-Meteo.

    Por diretriz de governança, o endpoint público gratuito da Open-Meteo
    NÃO é ativado como fonte de produção sem autorização contratual explícita.
    """

    def __init__(
        self,
        api_base_url: str = "https://api.open-meteo.com/v1/forecast",
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
        is_licensed: bool = False,
        allow_unlicensed_public: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider_id = "OPEN_METEO"
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.is_licensed = is_licensed
        self.allow_unlicensed_public = allow_unlicensed_public
        self._client = client

    async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
        """Executa a consulta agrometeorológica no Open-Meteo.

        Raises:
            ProviderUnlicensedError: Se a licença não estiver ativa nem for permitido
                uso público.
            ProviderTimeoutError: Se ocorrer timeout na requisição.
            ProviderUnavailableError: Se o serviço upstream retornar erro HTTP ou conexão falhar.
        """
        if not self.is_licensed and not self.allow_unlicensed_public:
            raise ProviderUnlicensedError(
                "Provedor Open-Meteo não licenciado para uso público em produção."
            )

        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
            ),
            "hourly": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation_probability,precipitation,weather_code,"
                "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
            ),
            "timezone": "auto",
            "forecast_days": 7,
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "temperature_unit": "celsius",
        }
        if self.api_key:
            params["apikey"] = self.api_key

        try:
            if self._client:
                resp = await self._client.get(
                    self.api_base_url, params=params, timeout=self.timeout_seconds
                )
                resp.raise_for_status()
                payload = resp.json()
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.get(self.api_base_url, params=params)
                    resp.raise_for_status()
                    payload = resp.json()
        except httpx.TimeoutException as exc:
            logger.warning("Timeout ao consultar Open-Meteo", lat=lat, lon=lon)
            raise ProviderTimeoutError(f"Timeout na consulta meteorológica: {exc}") from exc
        except (httpx.HTTPError, OSError) as exc:
            logger.error("Falha ao comunicar com Open-Meteo", error=str(exc))
            raise ProviderUnavailableError(f"Provedor meteorológico indisponível: {exc}") from exc

        return self._normalize_payload(lat, lon, payload)

    def _normalize_payload(
        self, lat: float, lon: float, payload: dict[str, Any]
    ) -> ClimaPrevisaoResponse:
        """Converte a resposta do Open-Meteo para o contrato canônico do DeepFarms Agro."""
        now = datetime.now(timezone.utc)
        fuso = payload.get("timezone", "America/Sao_Paulo")
        current_data = payload.get("current", {})

        current_code = current_data.get("weather_code")
        desc, icone = self._translate_wmo(current_code)

        condicoes = CondicaoAtual(
            temperaturaC=current_data.get("temperature_2m"),
            sensacaoTermicaC=current_data.get("apparent_temperature"),
            umidadeRelativaPct=(
                int(round(current_data["relative_humidity_2m"]))
                if current_data.get("relative_humidity_2m") is not None
                else None
            ),
            ventoKmH=current_data.get("wind_speed_10m"),
            ventoDirecaoGraus=(
                int(round(current_data["wind_direction_10m"]))
                if current_data.get("wind_direction_10m") is not None
                else None
            ),
            ventoRajadasKmH=current_data.get("wind_gusts_10m"),
            precipitacaoMm=current_data.get("precipitation"),
            condicaoDescricao=desc,
            condicaoIcone=icone,
        )

        # Previsão horária: primeiras 24 horas
        horaria_list: list[PrevisaoHorariaItem] = []
        hourly_data = payload.get("hourly", {})
        times = hourly_data.get("time", [])
        temps = hourly_data.get("temperature_2m", [])
        apparents = hourly_data.get("apparent_temperature", [])
        humidities = hourly_data.get("relative_humidity_2m", [])
        winds = hourly_data.get("wind_speed_10m", [])
        wind_dirs = hourly_data.get("wind_direction_10m", [])
        gusts = hourly_data.get("wind_gusts_10m", [])
        precips = hourly_data.get("precipitation", [])
        precip_probs = hourly_data.get("precipitation_probability", [])
        codes = hourly_data.get("weather_code", [])

        for i in range(min(24, len(times))):
            h_desc, h_icon = self._translate_wmo(codes[i] if i < len(codes) else None)
            horaria_list.append(
                PrevisaoHorariaItem(
                    horaIso=times[i],
                    temperaturaC=temps[i] if i < len(temps) else None,
                    sensacaoTermicaC=apparents[i] if i < len(apparents) else None,
                    umidadePct=(
                        int(round(humidities[i]))
                        if i < len(humidities) and humidities[i] is not None
                        else None
                    ),
                    ventoKmH=winds[i] if i < len(winds) else None,
                    ventoDirecaoGraus=(
                        int(round(wind_dirs[i]))
                        if i < len(wind_dirs) and wind_dirs[i] is not None
                        else None
                    ),
                    ventoRajadasKmH=gusts[i] if i < len(gusts) else None,
                    precipitacaoMm=precips[i] if i < len(precips) else None,
                    probabilidadeChuvaPct=(
                        int(round(precip_probs[i]))
                        if i < len(precip_probs) and precip_probs[i] is not None
                        else None
                    ),
                    condicaoDescricao=h_desc,
                    condicaoIcone=h_icon,
                )
            )

        # Previsão diária: até 7 dias
        diaria_list: list[PrevisaoDiariaItem] = []
        daily_data = payload.get("daily", {})
        d_times = daily_data.get("time", [])
        d_maxs = daily_data.get("temperature_2m_max", [])
        d_mins = daily_data.get("temperature_2m_min", [])
        d_precips = daily_data.get("precipitation_sum", [])
        d_probs = daily_data.get("precipitation_probability_max", [])
        d_winds = daily_data.get("wind_speed_10m_max", [])
        d_codes = daily_data.get("weather_code", [])

        for i in range(min(7, len(d_times))):
            d_desc, d_icon = self._translate_wmo(d_codes[i] if i < len(d_codes) else None)
            d_iso = d_times[i]
            try:
                dt_dia = date.fromisoformat(d_iso)
                dia_semana = DIAS_SEMANA_PT[dt_dia.weekday()]
            except ValueError:
                dia_semana = "hoje" if i == 0 else f"dia {i+1}"

            diaria_list.append(
                PrevisaoDiariaItem(
                    dataIso=d_iso,
                    diaSemana=dia_semana,
                    tempMinC=d_mins[i] if i < len(d_mins) else None,
                    tempMaxC=d_maxs[i] if i < len(d_maxs) else None,
                    precipitacaoMm=d_precips[i] if i < len(d_precips) else None,
                    probabilidadeChuvaPct=(
                        int(round(d_probs[i]))
                        if i < len(d_probs) and d_probs[i] is not None
                        else None
                    ),
                    ventoMaxKmH=d_winds[i] if i < len(d_winds) else None,
                    condicaoDescricao=d_desc,
                    condicaoIcone=d_icon,
                )
            )

        valido_ate = now.replace(minute=59, second=59)

        return ClimaPrevisaoResponse(
            latitude=lat,
            longitude=lon,
            latitudeGrid=lat,
            longitudeGrid=lon,
            fusoHorario=fuso,
            provedor=self.provider_id,
            licencaFonte="Creative Commons Attribution 4.0 International (CC BY 4.0) - Open-Meteo",
            tipoDado="PREVISTO",
            dadosSinteticos=False,
            temperaturaAtualC=condicoes.temperaturaC,
            sensacaoTermicaC=condicoes.sensacaoTermicaC,
            umidadeRelativaPct=condicoes.umidadeRelativaPct,
            ventoVelocidadeKmH=condicoes.ventoKmH,
            ventoDirecaoGraus=condicoes.ventoDirecaoGraus,
            ventoRajadasKmH=condicoes.ventoRajadasKmH,
            precipitacaoMm=condicoes.precipitacaoMm,
            probabilidadeChuvaPct=condicoes.probabilidadeChuvaPct,
            condicaoDescricao=condicoes.condicaoDescricao,
            condicaoIcone=condicoes.condicaoIcone,
            condicoesAtuais=condicoes,
            previsaoHoraria=horaria_list,
            previsaoDiaria=diaria_list,
            horarioReferenciaIso=now,
            obtidoEmIso=now,
            validoAteIso=valido_ate,
            emCache=False,
            desatualizado=False,
            statusOperacional="NORMAL",
        )

    @staticmethod
    def _translate_wmo(code: int | None) -> tuple[str | None, str | None]:
        if code is None:
            return None, None
        return WMO_INTERPRETATION.get(code, ("Tempo variável", "CloudSun"))


OPENWEATHER_ICON_MAP: dict[str, str] = {
    "01d": "Sun",
    "01n": "Moon",
    "02d": "CloudSun",
    "02n": "CloudMoon",
    "03d": "Cloud",
    "03n": "Cloud",
    "04d": "Cloud",
    "04n": "Cloud",
    "09d": "CloudDrizzle",
    "09n": "CloudDrizzle",
    "10d": "CloudRain",
    "10n": "CloudRain",
    "11d": "CloudLightning",
    "11n": "CloudLightning",
    "13d": "CloudSnow",
    "13n": "CloudSnow",
    "50d": "CloudFog",
    "50n": "CloudFog",
}


class OpenWeatherOneCallAdapter:
    """Adaptador para a API OpenWeather One Call 3.0.

    Preparado para integração real e independente com chave própria do DeepFarms Agro.
    Por governança de conformidade estrita, requer is_licensed=True e api_key válida.
    """

    def __init__(
        self,
        api_base_url: str = "https://api.openweathermap.org/data/3.0/onecall",
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
        is_licensed: bool = False,
        allow_unlicensed_public: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider_id = "OPENWEATHER"
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.is_licensed = is_licensed
        self.allow_unlicensed_public = allow_unlicensed_public
        self._client = client

    async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
        """Executa consulta agrometeorológica no OpenWeather One Call 3.0.

        Args:
            lat: Latitude em graus (-90 a 90).
            lon: Longitude em graus (-180 a 180).

        Returns:
            ClimaPrevisaoResponse normalizada.

        Raises:
            ProviderUnlicensedError: Se não licenciado ou chave de API ausente.
            ProviderTimeoutError: Se ocorrer timeout na requisição.
            ProviderUnavailableError: Se o serviço upstream falhar.
        """
        if not self.is_licensed and not self.allow_unlicensed_public:
            raise ProviderUnlicensedError(
                "Provedor OpenWeather não licenciado para uso público em produção."
            )
        if not self.api_key:
            raise ProviderUnlicensedError(
                "Chave de API do OpenWeather (One Call 3.0) não configurada."
            )

        params: dict[str, Any] = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "pt_br",
            "exclude": "minutely,alerts",
        }

        try:
            if self._client:
                resp = await self._client.get(
                    self.api_base_url, params=params, timeout=self.timeout_seconds
                )
                resp.raise_for_status()
                payload = resp.json()
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.get(self.api_base_url, params=params)
                    resp.raise_for_status()
                    payload = resp.json()
        except httpx.TimeoutException as exc:
            logger.warning("Timeout ao consultar OpenWeather", lat=lat, lon=lon)
            raise ProviderTimeoutError(f"Timeout na consulta meteorológica: {exc}") from exc
        except (httpx.HTTPError, OSError) as exc:
            logger.error("Falha ao comunicar com OpenWeather", error=str(exc))
            raise ProviderUnavailableError(f"Provedor meteorológico indisponível: {exc}") from exc

        return self._normalize_payload(lat, lon, payload)

    def _normalize_payload(
        self, lat: float, lon: float, payload: dict[str, Any]
    ) -> ClimaPrevisaoResponse:
        """Converte a resposta One Call 3.0 para o contrato do DeepFarms Agro."""
        now = datetime.now(timezone.utc)
        fuso = payload.get("timezone", "America/Sao_Paulo")
        current_data = payload.get("current", {})

        desc, icone = self._extract_weather(current_data.get("weather"))
        wind_speed_kmh = self._to_kmh(current_data.get("wind_speed"))
        wind_gust_kmh = self._to_kmh(current_data.get("wind_gust"))
        precip = self._extract_rain(current_data.get("rain"))

        condicoes = CondicaoAtual(
            temperaturaC=current_data.get("temp"),
            sensacaoTermicaC=current_data.get("feels_like"),
            umidadeRelativaPct=current_data.get("humidity"),
            ventoKmH=wind_speed_kmh,
            ventoDirecaoGraus=current_data.get("wind_deg"),
            ventoRajadasKmH=wind_gust_kmh,
            precipitacaoMm=precip,
            condicaoDescricao=desc,
            condicaoIcone=icone,
        )

        horaria_list = self._build_hourly(payload.get("hourly", []))
        diaria_list = self._build_daily(payload.get("daily", []))
        valido_ate = now.replace(minute=59, second=59)

        return ClimaPrevisaoResponse(
            latitude=lat,
            longitude=lon,
            latitudeGrid=lat,
            longitudeGrid=lon,
            fusoHorario=fuso,
            provedor=self.provider_id,
            licencaFonte="OpenWeather One Call 3.0 - Licenciamento Comercial / Pay-as-you-call",
            tipoDado="PREVISTO",
            dadosSinteticos=False,
            temperaturaAtualC=condicoes.temperaturaC,
            sensacaoTermicaC=condicoes.sensacaoTermicaC,
            umidadeRelativaPct=condicoes.umidadeRelativaPct,
            ventoVelocidadeKmH=condicoes.ventoKmH,
            ventoDirecaoGraus=condicoes.ventoDirecaoGraus,
            ventoRajadasKmH=condicoes.ventoRajadasKmH,
            precipitacaoMm=condicoes.precipitacaoMm,
            probabilidadeChuvaPct=condicoes.probabilidadeChuvaPct,
            condicaoDescricao=condicoes.condicaoDescricao,
            condicaoIcone=condicoes.condicaoIcone,
            condicoesAtuais=condicoes,
            previsaoHoraria=horaria_list,
            previsaoDiaria=diaria_list,
            horarioReferenciaIso=now,
            obtidoEmIso=now,
            validoAteIso=valido_ate,
            emCache=False,
            desatualizado=False,
            statusOperacional="NORMAL",
        )

    def _build_hourly(self, items: list[dict[str, Any]]) -> list[PrevisaoHorariaItem]:
        """Gera lista horária para as primeiras 24 horas."""
        horaria: list[PrevisaoHorariaItem] = []
        for item in items[:24]:
            h_desc, h_icon = self._extract_weather(item.get("weather"))
            dt_epoch = item.get("dt", 0)
            iso_time = datetime.fromtimestamp(dt_epoch, tz=timezone.utc).isoformat()
            pop_pct = int(round(item["pop"] * 100)) if item.get("pop") is not None else None
            horaria.append(
                PrevisaoHorariaItem(
                    horaIso=iso_time,
                    temperaturaC=item.get("temp"),
                    sensacaoTermicaC=item.get("feels_like"),
                    umidadePct=item.get("humidity"),
                    ventoKmH=self._to_kmh(item.get("wind_speed")),
                    ventoDirecaoGraus=item.get("wind_deg"),
                    ventoRajadasKmH=self._to_kmh(item.get("wind_gust")),
                    precipitacaoMm=self._extract_rain(item.get("rain")),
                    probabilidadeChuvaPct=pop_pct,
                    condicaoDescricao=h_desc,
                    condicaoIcone=h_icon,
                )
            )
        return horaria

    def _build_daily(self, items: list[dict[str, Any]]) -> list[PrevisaoDiariaItem]:
        """Gera lista diária para até 7 dias."""
        diaria: list[PrevisaoDiariaItem] = []
        for item in items[:7]:
            d_desc, d_icon = self._extract_weather(item.get("weather"))
            dt_epoch = item.get("dt", 0)
            dt_obj = datetime.fromtimestamp(dt_epoch, tz=timezone.utc)
            d_iso = dt_obj.strftime("%Y-%m-%d")
            dia_semana = DIAS_SEMANA_PT[dt_obj.weekday()]
            temp_dict = item.get("temp", {})
            pop_pct = int(round(item["pop"] * 100)) if item.get("pop") is not None else None
            diaria.append(
                PrevisaoDiariaItem(
                    dataIso=d_iso,
                    diaSemana=dia_semana,
                    tempMinC=temp_dict.get("min"),
                    tempMaxC=temp_dict.get("max"),
                    precipitacaoMm=item.get("rain"),
                    probabilidadeChuvaPct=pop_pct,
                    ventoMaxKmH=self._to_kmh(item.get("wind_speed")),
                    condicaoDescricao=d_desc,
                    condicaoIcone=d_icon,
                )
            )
        return diaria

    @staticmethod
    def _extract_weather(weather_list: list[dict[str, Any]] | None) -> tuple[str | None, str | None]:
        if not weather_list or not isinstance(weather_list, list):
            return None, None
        w = weather_list[0]
        desc = w.get("description", "").capitalize() or None
        icon_code = w.get("icon", "")
        return desc, OPENWEATHER_ICON_MAP.get(icon_code, "CloudSun")

    @staticmethod
    def _to_kmh(speed_ms: float | None) -> float | None:
        if speed_ms is None:
            return None
        return round(speed_ms * 3.6, 1)

    @staticmethod
    def _extract_rain(rain_obj: Any) -> float | None:
        if isinstance(rain_obj, (int, float)):
            return float(rain_obj)
        if isinstance(rain_obj, dict):
            return float(rain_obj.get("1h", 0.0))
        return None


class WeatherAPIAdapter:
    """Adaptador agrometeorológico para WeatherAPI (v1/forecast.json).

    Provedor principal candidato para o piloto do DeepFarms Agro.
    Suporta plano Free (até 3 dias) e Starter (até 7 dias) sem preenchimento artificial.
    """

    def __init__(
        self,
        api_base_url: str = "https://api.weatherapi.com/v1",
        api_key: str | None = None,
        is_enabled: bool = False,
        max_days: int = 3,
        timeout_seconds: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider_id = "WEATHERAPI"
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key or ""
        self.is_enabled = is_enabled
        self.is_licensed = is_enabled and bool(self.api_key)
        self.max_days = max(1, min(max_days, 14))
        self.timeout_seconds = timeout_seconds
        self._client = client

    def __repr__(self) -> str:
        return f"<WeatherAPIAdapter enabled={self.is_enabled} max_days={self.max_days}>"

    def __str__(self) -> str:
        return self.__repr__()

    async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
        """Executa consulta agrometeorológica na WeatherAPI v1/forecast.json.

        Args:
            lat: Latitude em graus (-90 a 90).
            lon: Longitude em graus (-180 a 180).

        Returns:
            ClimaPrevisaoResponse normalizada.

        Raises:
            ProviderUnlicensedError: Se desabilitado ou sem chave configurada.
            ProviderAuthenticationError: Se a chave for inválida ou desabilitada.
            ProviderQuotaExceededError: Se a franquia da WeatherAPI for esgotada.
            ProviderLocationNotFoundError: Se a localidade não for encontrada.
            ProviderTimeoutError: Se ocorrer timeout na requisição.
            ProviderUnavailableError: Se o serviço upstream falhar.
        """
        if not self.is_enabled or not self.api_key:
            raise ProviderUnlicensedError(
                "Provedor WeatherAPI não está habilitado ou credencial não informada."
            )

        resp = await self._send_request(lat, lon)
        if resp.status_code != 200:
            self._handle_api_error(resp)

        try:
            payload = resp.json()
        except Exception as exc:
            raise ProviderUnavailableError("Resposta da WeatherAPI não é um JSON válido.") from exc

        return self._normalize_payload(lat, lon, payload)

    async def _send_request(self, lat: float, lon: float) -> httpx.Response:
        """Envia requisição HTTP com parâmetros sanitizados.

        Args:
            lat: Latitude geográfica.
            lon: Longitude geográfica.

        Returns:
            httpx.Response da requisição.
        """
        url = f"{self.api_base_url}/forecast.json"
        params = {
            "key": self.api_key,
            "q": f"{lat:.4f},{lon:.4f}",
            "days": self.max_days,
            "aqi": "no",
            "alerts": "no",
            "lang": "pt",
        }
        try:
            if self._client:
                return await self._client.get(url, params=params, timeout=self.timeout_seconds)
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                return await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            logger.warning("Timeout ao consultar WeatherAPI", lat=lat, lon=lon)
            raise ProviderTimeoutError("Tempo limite esgotado ao consultar WeatherAPI") from exc
        except (httpx.HTTPError, OSError) as exc:
            logger.error("Falha de conexão com WeatherAPI", error=str(exc))
            raise ProviderUnavailableError("Serviço WeatherAPI indisponível") from exc

    def _handle_api_error(self, resp: httpx.Response) -> None:
        """Mapeia os códigos de erro documentados da WeatherAPI sem expor segredos.

        Args:
            resp: Resposta HTTP com status diferente de 200.
        """
        code = None
        try:
            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                code = data["error"].get("code")
        except Exception:
            pass

        logger.warning("Erro retornado pela WeatherAPI", status_code=resp.status_code, error_code=code)
        if code == 1002:
            raise ProviderUnconfiguredError("Chave de API não informada à WeatherAPI.")
        if code in (2006, 1005):
            raise ProviderAuthenticationError("Chave de API da WeatherAPI inválida.")
        if code == 2007:
            raise ProviderQuotaExceededError("Franquia mensal da WeatherAPI esgotada.")
        if code == 2008:
            raise ProviderAuthenticationError("Chave da WeatherAPI desabilitada pelo fornecedor.")
        if code == 2009:
            raise ProviderUnlicensedError("Recurso não disponível no plano contratado da WeatherAPI.")
        if code == 1006:
            raise ProviderLocationNotFoundError("Coordenadas não localizadas na base da WeatherAPI.")
        if code == 9999 or resp.status_code >= 500:
            raise ProviderUnavailableError("Serviço da WeatherAPI temporariamente indisponível.")
        raise ProviderUnavailableError(f"Erro na comunicação com WeatherAPI (status {resp.status_code}).")

    def _normalize_payload(
        self, lat: float, lon: float, payload: dict[str, Any]
    ) -> ClimaPrevisaoResponse:
        """Converte a resposta oficial da WeatherAPI para o contrato DeepFarms Agro.

        Args:
            lat: Latitude requisitada.
            lon: Longitude requisitada.
            payload: Dicionário retornado pela API da WeatherAPI.

        Returns:
            ClimaPrevisaoResponse normalizada.
        """
        now = datetime.now(timezone.utc)
        location = payload.get("location") or {}
        current = payload.get("current") or {}
        forecast = payload.get("forecast") or {}
        forecastdays = forecast.get("forecastday", [])

        fuso = location.get("tz_id") or "America/Sao_Paulo"
        ref_epoch = location.get("localtime_epoch") or current.get("last_updated_epoch") or int(now.timestamp())

        condicoes = self._build_condicoes_atuais(current, forecastdays)
        horaria = self._build_hourly_24h(forecastdays, ref_epoch)
        diaria = self._build_daily(forecastdays)
        valido_ate = now.replace(minute=59, second=59)

        return ClimaPrevisaoResponse(
            latitude=lat,
            longitude=lon,
            latitudeGrid=lat,
            longitudeGrid=lon,
            fusoHorario=fuso,
            provedor=self.provider_id,
            licencaFonte="WeatherAPI.com - Previsão Meteorológica (Powered by WeatherAPI.com)",
            tipoDado="PREVISTO",
            dadosSinteticos=False,
            temperaturaAtualC=condicoes.temperaturaC,
            sensacaoTermicaC=condicoes.sensacaoTermicaC,
            umidadeRelativaPct=condicoes.umidadeRelativaPct,
            ventoVelocidadeKmH=condicoes.ventoKmH,
            ventoDirecaoGraus=condicoes.ventoDirecaoGraus,
            ventoRajadasKmH=condicoes.ventoRajadasKmH,
            precipitacaoMm=condicoes.precipitacaoMm,
            probabilidadeChuvaPct=condicoes.probabilidadeChuvaPct,
            condicaoDescricao=condicoes.condicaoDescricao,
            condicaoIcone=condicoes.condicaoIcone,
            condicoesAtuais=condicoes,
            previsaoHoraria=horaria,
            previsaoDiaria=diaria,
            horarioReferenciaIso=now,
            obtidoEmIso=now,
            validoAteIso=valido_ate,
            emCache=False,
            desatualizado=False,
            statusOperacional="NORMAL",
        )

    def _build_condicoes_atuais(
        self, current: dict[str, Any], forecastdays: list[dict[str, Any]]
    ) -> CondicaoAtual:
        """Normaliza as condições observadas atuais da WeatherAPI."""
        c_cond = current.get("condition") or {}
        prob_chuva = None
        if forecastdays:
            first_day = forecastdays[0].get("day") or {}
            prob_chuva = first_day.get("daily_chance_of_rain")

        return CondicaoAtual(
            temperaturaC=current.get("temp_c"),
            sensacaoTermicaC=current.get("feelslike_c"),
            umidadeRelativaPct=current.get("humidity"),
            ventoKmH=current.get("wind_kph"),
            ventoDirecaoGraus=current.get("wind_degree"),
            ventoRajadasKmH=current.get("gust_kph"),
            precipitacaoMm=current.get("precip_mm"),
            probabilidadeChuvaPct=prob_chuva,
            condicaoDescricao=c_cond.get("text"),
            condicaoIcone=self._map_condition(c_cond.get("code"), is_day=current.get("is_day", 1)),
        )

    def _build_hourly_24h(
        self, forecastdays: list[dict[str, Any]], ref_epoch: int
    ) -> list[PrevisaoHorariaItem]:
        """Constrói horizonte contínuo de 24 horas a partir da hora de referência.

        Garante a transição fluida entre dias (inclusive meia-noite).
        """
        all_hours: list[dict[str, Any]] = []
        for f_day in forecastdays:
            all_hours.extend(f_day.get("hour", []))

        current_hour_epoch = ref_epoch - (ref_epoch % 3600)
        future_hours = [h for h in all_hours if h.get("time_epoch", 0) >= current_hour_epoch]
        selected = future_hours[:24] if len(future_hours) >= 24 else future_hours or all_hours[:24]

        result: list[PrevisaoHorariaItem] = []
        for h in selected:
            t_epoch = h.get("time_epoch", 0)
            iso_time = (
                datetime.fromtimestamp(t_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if t_epoch
                else h.get("time", "").replace(" ", "T") + ":00Z"
            )
            cond = h.get("condition") or {}
            result.append(
                PrevisaoHorariaItem(
                    horaIso=iso_time,
                    temperaturaC=h.get("temp_c"),
                    sensacaoTermicaC=h.get("feelslike_c"),
                    umidadePct=h.get("humidity"),
                    ventoKmH=h.get("wind_kph"),
                    ventoDirecaoGraus=h.get("wind_degree"),
                    ventoRajadasKmH=h.get("gust_kph"),
                    precipitacaoMm=h.get("precip_mm"),
                    probabilidadeChuvaPct=h.get("chance_of_rain"),
                    condicaoDescricao=cond.get("text"),
                    condicaoIcone=self._map_condition(cond.get("code"), is_day=h.get("is_day", 1)),
                )
            )
        return result

    def _build_daily(self, forecastdays: list[dict[str, Any]]) -> list[PrevisaoDiariaItem]:
        """Normaliza os dias disponíveis (até 3 no Free ou 7 no Starter)."""
        result: list[PrevisaoDiariaItem] = []
        for i, f_day in enumerate(forecastdays):
            date_str = f_day.get("date", "")
            try:
                dt_obj = date.fromisoformat(date_str)
                dia_semana = DIAS_SEMANA_PT[dt_obj.weekday()]
            except ValueError:
                dia_semana = "hoje" if i == 0 else f"dia {i+1}"

            day_info = f_day.get("day", {})
            cond = day_info.get("condition") or {}
            result.append(
                PrevisaoDiariaItem(
                    dataIso=date_str,
                    diaSemana=dia_semana,
                    tempMinC=day_info.get("mintemp_c"),
                    tempMaxC=day_info.get("maxtemp_c"),
                    precipitacaoMm=day_info.get("totalprecip_mm"),
                    probabilidadeChuvaPct=day_info.get("daily_chance_of_rain"),
                    ventoMaxKmH=day_info.get("maxwind_kph"),
                    condicaoDescricao=cond.get("text"),
                    condicaoIcone=self._map_condition(cond.get("code"), is_day=1),
                )
            )
        return result

    @staticmethod
    def _map_condition(code: int | None, is_day: int = 1) -> str:
        """Mapeia código meteorológico da WeatherAPI para os ícones do sistema."""
        if code is None:
            return "CloudSun" if is_day == 1 else "Cloud"
        if code == 1000:
            return "Sun"
        if code == 1003:
            return "CloudSun"
        if code in (1006, 1009):
            return "Cloud"
        if code in (1030, 1135, 1147):
            return "CloudFog"
        if code in (1150, 1153, 1168, 1171):
            return "CloudDrizzle"
        if code in (1063, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243, 1246):
            return "CloudRain"
        if code in (1087, 1273, 1276, 1279, 1282):
            return "CloudLightning"
        if code in (
            1066, 1069, 1072, 1114, 1117, 1198, 1201, 1204, 1207,
            1210, 1213, 1216, 1219, 1222, 1225, 1237, 1249, 1252,
            1255, 1258, 1261, 1264
        ):
            return "CloudSnow"
        return "CloudSun" if is_day == 1 else "Cloud"


class SyntheticFixtureAdapter:
    """Adaptador de testes para simulação determinística local.

    Todos os dados gerados por este adaptador são OBRIGATORIAMENTE rotulados
    como `dadosSinteticos=True` para blindagem contra desinformação ao usuário.
    """

    def __init__(
        self,
        provider_id: str = "FIXTURE_TESTE",
        simular_falha: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self.provider_id = provider_id
        self.is_licensed = True
        self.simular_falha = simular_falha
        self.delay_seconds = delay_seconds

    async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        if self.simular_falha:
            raise self.simular_falha

        now = datetime.now(timezone.utc)
        valido_ate = datetime.fromtimestamp(now.timestamp() + 1800, tz=timezone.utc)

        condicoes = CondicaoAtual(
            temperaturaC=24.5,
            sensacaoTermicaC=25.0,
            umidadeRelativaPct=62,
            ventoKmH=12.0,
            ventoDirecaoGraus=180,
            ventoRajadasKmH=18.5,
            precipitacaoMm=0.0,
            probabilidadeChuvaPct=10,
            condicaoDescricao="Parcialmente nublado",
            condicaoIcone="CloudSun",
        )

        horaria: list[PrevisaoHorariaItem] = [
            PrevisaoHorariaItem(
                horaIso=f"2026-10-22T{h:02d}:00:00Z",
                temperaturaC=20.0 + (h % 8),
                sensacaoTermicaC=21.0 + (h % 8),
                umidadePct=60 + (h % 20),
                ventoKmH=10.0 + (h % 5),
                precipitacaoMm=0.5 if h == 14 else 0.0,
                probabilidadeChuvaPct=40 if h == 14 else 5,
                condicaoDescricao="Sol entre nuvens",
                condicaoIcone="CloudSun",
            )
            for h in range(24)
        ]

        diaria: list[PrevisaoDiariaItem] = [
            PrevisaoDiariaItem(
                dataIso=f"2026-10-{22+d:02d}",
                diaSemana=DIAS_SEMANA_PT[d % 7],
                tempMinC=18.0 + d,
                tempMaxC=28.0 + d,
                precipitacaoMm=5.0 if d == 2 else 0.0,
                probabilidadeChuvaPct=60 if d == 2 else 10,
                ventoMaxKmH=20.0,
                condicaoDescricao="Chuva isolada" if d == 2 else "Ensolarado",
                condicaoIcone="CloudRain" if d == 2 else "Sun",
            )
            for d in range(7)
        ]

        return ClimaPrevisaoResponse(
            latitude=lat,
            longitude=lon,
            latitudeGrid=lat,
            longitudeGrid=lon,
            fusoHorario="America/Sao_Paulo",
            provedor=self.provider_id,
            licencaFonte="Dados sintéticos para testes e desenvolvimento",
            tipoDado="PREVISTO",
            dadosSinteticos=True,
            temperaturaAtualC=condicoes.temperaturaC,
            sensacaoTermicaC=condicoes.sensacaoTermicaC,
            umidadeRelativaPct=condicoes.umidadeRelativaPct,
            ventoVelocidadeKmH=condicoes.ventoKmH,
            ventoDirecaoGraus=condicoes.ventoDirecaoGraus,
            ventoRajadasKmH=condicoes.ventoRajadasKmH,
            precipitacaoMm=condicoes.precipitacaoMm,
            probabilidadeChuvaPct=condicoes.probabilidadeChuvaPct,
            condicaoDescricao=condicoes.condicaoDescricao,
            condicaoIcone=condicoes.condicaoIcone,
            condicoesAtuais=condicoes,
            previsaoHoraria=horaria,
            previsaoDiaria=diaria,
            horarioReferenciaIso=now,
            obtidoEmIso=now,
            validoAteIso=valido_ate,
            emCache=False,
            desatualizado=False,
            statusOperacional="NORMAL",
        )


def verify_provider_public_authorization(
    provider_slug: str,
    cfg: Any = None,
    credentials: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Verifica se o provedor possui autorização contratual e técnica estrita para o ambiente público.

    Retorna (autorizado: bool, motivo: str).

    Diretrizes de Governança e Compliance:
    - OPEN_METEO: NUNCA autorizado em ambiente público sem comprovação de licença contratual
      (chave comercial cadastrada em settings.open_meteo_api_key OU confirmação explícita de licença
      em settings.open_meteo_licensed E cfg.open_meteo_licensed, ou allow_unlicensed_public em dev/staging).
      Uma flag isolada no banco de dados (cfg.open_meteo_licensed) SEM respaldo em ambiente NÃO autoriza o uso.
    - OPENWEATHER: Requer credencial válida configurada E confirmação de licença comercial (settings.openweather_licensed
      ou cfg.openweather_licensed com chave One Call 3.0 paga) ou allow_unlicensed_public.
    - WEATHERAPI: Requer chave de API válida cadastrada no cofre ou no ambiente.
    - Adaptadores sintéticos de teste: autorizados se identificados por SYNTHETIC ou TEST.
    """
    slug = provider_slug.upper()

    if "SYNTHETIC" in slug or slug.startswith("TEST"):
        return True, "Adaptador sintético autorizado para testes."

    if slug == "OPEN_METEO":
        has_enterprise_key = bool(settings.open_meteo_api_key)
        cfg_licensed = getattr(cfg, "open_meteo_licensed", False) if cfg is not None else False
        has_contract_attestation = bool(settings.open_meteo_licensed) and bool(cfg_licensed)
        has_dev_allow = bool(settings.open_meteo_allow_unlicensed_public)
        if has_enterprise_key or has_contract_attestation or has_dev_allow:
            return True, "Open-Meteo autorizado para uso público."
        return False, (
            "Open-Meteo exige licença contratual explícita ou chave enterprise para uso em ambiente público "
            "(uma flag técnica isolada no banco de dados não comprova licenciamento contratual)."
        )

    if slug == "OPENWEATHER":
        creds = credentials or {}
        cred_val = creds.get("OPENWEATHER")
        has_cred = bool(cred_val) or bool(settings.openweather_api_key)
        if not has_cred:
            return False, "OpenWeather requer credencial de API configurada."
        cfg_licensed = getattr(cfg, "openweather_licensed", False) if cfg is not None else False
        has_license = bool(cfg_licensed or settings.openweather_licensed)
        has_dev_allow = bool(settings.openweather_allow_unlicensed_public)
        if has_license or has_dev_allow:
            return True, "OpenWeather autorizado para uso público."
        return False, "OpenWeather One Call 3.0 requer confirmação de licença comercial ativa."

    if slug == "WEATHERAPI":
        if not settings.weatherapi_enabled:
            return False, "WeatherAPI está desabilitada por WEATHERAPI_ENABLED."
        creds = credentials or {}
        cred_val = creds.get("WEATHERAPI")
        has_cred = bool(cred_val) or bool(settings.weatherapi_api_key)
        if has_cred:
            return True, "WeatherAPI autorizado com credencial configurada."
        return False, "WeatherAPI requer credencial de API válida configurada no cofre seguro."

    return False, f"Provedor desconhecido: '{provider_slug}'"


def is_provider_authorized_for_public(
    provider_slug: str,
    cfg: Any = None,
    credentials: dict[str, Any] | None = None,
) -> bool:
    """Verifica se o provedor possui autorização contratual e técnica estrita para o ambiente público."""
    authorized, _ = verify_provider_public_authorization(provider_slug, cfg, credentials)
    return authorized

