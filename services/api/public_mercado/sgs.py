"""Cliente e contratos para as séries oficiais do SGS do Banco Central do Brasil."""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
BCB_SGS_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
AVISO_LEGAL_BCB = "Dados públicos oficiais divulgados pelo Banco Central do Brasil (BCB) e IBGE. Não constituem recomendação de investimento."

# Códigos de séries oficiais homologadas
SERIE_META_SELIC = 432       # Taxa de juros - Meta Selic definida pelo Copom (% a.a.)
SERIE_IPCA_MENSAL = 433      # Índice nacional de preços ao consumidor-amplo (IPCA) - Var. % mensal
SERIE_IPCA_12M = 13522       # Índice nacional de preços ao consumidor-amplo (IPCA) - em 12 meses (% 12m)
SERIE_EURO_VENDA = 21619     # Taxa de câmbio - Euro (venda) (BRL/EUR)
SERIE_EURO_COMPRA = 21620    # Taxa de câmbio - Euro (compra) (BRL/EUR)


class SgsObservation(BaseModel):
    """Observação individual retornada pelo SGS."""
    model_config = ConfigDict(extra="forbid")

    data: date
    valor: float = Field(allow_inf_nan=False)


class IndicadorMacroItem(BaseModel):
    """Item canônico de indicador macroeconômico."""
    model_config = ConfigDict(extra="forbid")

    id: str
    nomeOficial: str
    codigoSerieBcb: int
    valor: float = Field(allow_inf_nan=False)
    valorCompra: float | None = None
    valorVenda: float | None = None
    unidade: str
    periodicidade: str
    dataReferencia: str  # YYYY-MM-DD
    dataConsultaIso: datetime
    fonteOficial: str
    estadoDisponibilidade: str
    estaDesatualizado: bool
    avisoLegal: str = AVISO_LEGAL_BCB


class IndicadoresMacroPayload(BaseModel):
    """Agrupamento interno para cache com suporte a falha e fallback granular."""
    model_config = ConfigDict(extra="forbid")

    selic: SgsObservation | None = None
    ipca_mensal: SgsObservation | None = None
    ipca_12m: SgsObservation | None = None
    euro_venda: SgsObservation | None = None
    euro_compra: SgsObservation | None = None
    dataApuracaoIso: datetime
    seriesFallback: list[str] = Field(default_factory=list)


class IndicadoresMacroResponse(BaseModel):
    """Contrato da resposta pública de indicadores macroeconômicos."""
    model_config = ConfigDict(extra="forbid")

    sucesso: bool
    versao: str = "1.0"
    dataConsultaIso: datetime
    cacheAtualizadoEmIso: datetime | None = None
    estadoDisponibilidade: str
    estaDesatualizado: bool
    avisoLegal: str = AVISO_LEGAL_BCB
    itens: list[IndicadorMacroItem]


def parse_sgs_date(raw_date: str) -> date:
    """Converte 'DD/MM/YYYY' do SGS para date."""
    try:
        parts = raw_date.strip().split("/")
        if len(parts) != 3:
            raise ValueError(f"Formato de data SGS inválido: {raw_date}")
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except Exception as exc:
        raise ValueError(f"Data SGS não reconhecida '{raw_date}': {exc}") from exc


def parse_sgs_json(raw_text: str) -> list[SgsObservation]:
    """Valida e converte a resposta JSON do SGS do Banco Central."""
    try:
        data = json.loads(raw_text)
    except Exception as exc:
        raise ValueError(f"JSON SGS malformado: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("Resposta SGS deve ser uma lista de observações")

    observations: list[SgsObservation] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_val = item.get("valor")
        raw_dt = item.get("data")
        if raw_val is None or raw_dt is None:
            continue
        try:
            val_float = float(str(raw_val).replace(",", "."))
            if not math.isfinite(val_float):
                continue
            parsed_dt = parse_sgs_date(str(raw_dt))
            observations.append(SgsObservation(data=parsed_dt, valor=val_float))
        except (ValueError, TypeError):
            continue

    if not observations:
        raise ValueError("Nenhuma observação válida encontrada no retorno do SGS")
    return observations


class BcbSgsClient:
    """Cliente assíncrono para o Sistema Gerenciador de Séries Temporais do BCB."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

    async def fetch_serie_latest(self, codigo_serie: int, max_date: date | None = None) -> SgsObservation:
        """Busca a última observação válida de uma série do SGS até a data limite informada."""
        today = max_date or datetime.now(SAO_PAULO).date()
        # Séries com projeção de ciclo Copom (ex: Meta Selic) preenchem dias futuros;
        # O SGS limita /ultimos a 20 registros. Esse intervalo cobre a projeção
        # corrente e permite selecionar a observação vigente até hoje.
        qtd = 20 if codigo_serie == SERIE_META_SELIC else 1
        url = f"{BCB_SGS_BASE_URL}.{codigo_serie}/dados/ultimos/{qtd}?formato=json"
        if self.client is not None:
            return await self._request(self.client, url, max_date=today)

        limits = httpx.Limits(max_connections=3, max_keepalive_connections=2)
        async with httpx.AsyncClient(timeout=8.0, limits=limits, follow_redirects=False) as client:
            return await self._request(client, url, max_date=today)

    async def fetch_series_dict(self) -> dict[str, SgsObservation | Exception]:
        """Busca concorrentemente as 5 séries com tolerância e isolamento individual de falhas."""
        if self.client is not None:
            return await self._fetch_dict_with_client(self.client)

        limits = httpx.Limits(max_connections=5, max_keepalive_connections=3)
        async with httpx.AsyncClient(timeout=8.0, limits=limits, follow_redirects=False) as client:
            return await self._fetch_dict_with_client(client)

    async def _fetch_dict_with_client(self, client: httpx.AsyncClient) -> dict[str, SgsObservation | Exception]:
        import asyncio

        today = datetime.now(SAO_PAULO).date()
        keys = ["selic", "ipca_mensal", "ipca_12m", "euro_venda", "euro_compra"]
        series_codes = [SERIE_META_SELIC, SERIE_IPCA_MENSAL, SERIE_IPCA_12M, SERIE_EURO_VENDA, SERIE_EURO_COMPRA]
        
        tasks = []
        for code in series_codes:
            # Meta Selic (432) projeta calendário Copom para datas futuras; consulta histórico recente para filtrar até hoje
            qtd = 20 if code == SERIE_META_SELIC else 1
            url = f"{BCB_SGS_BASE_URL}.{code}/dados/ultimos/{qtd}?formato=json"
            tasks.append(self._request(client, url, max_date=today))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return dict(zip(keys, results))

    async def fetch_all_macro(self) -> IndicadoresMacroPayload:
        """Busca concorrentemente todas as 5 séries. Levanta exceção se qualquer uma falhar (compatibilidade estrita)."""
        dict_results = await self.fetch_series_dict()
        for k, v in dict_results.items():
            if isinstance(v, Exception):
                raise v
        return IndicadoresMacroPayload(
            selic=dict_results["selic"],  # type: ignore[arg-type]
            ipca_mensal=dict_results["ipca_mensal"],  # type: ignore[arg-type]
            ipca_12m=dict_results["ipca_12m"],  # type: ignore[arg-type]
            euro_venda=dict_results["euro_venda"],  # type: ignore[arg-type]
            euro_compra=dict_results["euro_compra"],  # type: ignore[arg-type]
            dataApuracaoIso=datetime.now(timezone.utc),
            seriesFallback=[],
        )

    @staticmethod
    async def _request(client: httpx.AsyncClient, url: str, max_date: date | None = None) -> SgsObservation:
        headers = {
            "Accept": "application/json",
            "User-Agent": "DeepFarms-Agro-Client/1.0",
        }
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        observations = parse_sgs_json(response.text)
        if max_date is not None:
            valid_observations = [o for o in observations if o.data <= max_date]
            if valid_observations:
                return valid_observations[-1]
        return observations[-1]
