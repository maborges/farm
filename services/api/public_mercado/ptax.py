"""Cliente e contrato da PTAX de fechamento USD/BRL."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
BCB_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
)
AVISO = "A PTAX é uma taxa de referência publicada pelo Banco Central do Brasil. Não representa cotação de câmbio em tempo real."


class PtaxQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cotacaoCompra: float = Field(gt=0, allow_inf_nan=False)
    cotacaoVenda: float = Field(gt=0, allow_inf_nan=False)
    dataHoraBoletimIso: datetime

    @field_validator("dataHoraBoletimIso")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("boletim sem fuso")
        return value


class PtaxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sucesso: bool
    versao: str = "1.0"
    indicador: str = "DOLAR_PTAX"
    moeda: str = "USD"
    moedaReferencia: str = "BRL"
    cotacaoCompra: float | None = None
    cotacaoVenda: float | None = None
    dataCotacao: str | None = None
    dataHoraBoletimIso: datetime | None = None
    tipoBoletim: str | None = None
    fonteOficial: str = "Banco Central do Brasil (BCB)"
    dataConsultaIso: datetime
    cacheAtualizadoEmIso: datetime | None = None
    estadoDisponibilidade: str
    estadoCotacao: str
    estaDesatualizado: bool
    avisoLegal: str = AVISO


def public_response(
    quote: PtaxQuote | None,
    consulted: datetime,
    synced: datetime | None,
    availability: str,
) -> PtaxResponse:
    return PtaxResponse(
        sucesso=quote is not None,
        cotacaoCompra=quote.cotacaoCompra if quote else None,
        cotacaoVenda=quote.cotacaoVenda if quote else None,
        dataCotacao=quote.dataHoraBoletimIso.astimezone(SAO_PAULO).date().isoformat() if quote else None,
        dataHoraBoletimIso=quote.dataHoraBoletimIso if quote else None,
        tipoBoletim="Fechamento PTAX" if quote else None,
        dataConsultaIso=consulted,
        cacheAtualizadoEmIso=synced,
        estadoDisponibilidade=availability,
        estadoCotacao=("ULTIMO_FECHAMENTO_CONHECIDO" if availability != "NORMAL" else "ULTIMO_FECHAMENTO_OFICIAL") if quote else "SEM_COTACAO",
        estaDesatualizado=quote is not None and availability != "NORMAL",
    )


class BcbPtaxClient:
    """Consulta somente a série diária oficial do dólar (PTAX de fechamento)."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

    async def fetch(self, now: datetime) -> PtaxQuote | None:
        local_date = now.astimezone(SAO_PAULO).date()
        data_inicial = f"{(local_date - timedelta(days=14)):%m-%d-%Y}"
        data_final = f"{local_date:%m-%d-%Y}"
        url = (
            f"{BCB_URL}?"
            f"@dataInicial='{data_inicial}'"
            f"&@dataFinalCotacao='{data_final}'"
            f"&$top=1&$orderby=dataHoraCotacao%20desc&$format=json"
        )
        if self.client is not None:
            return await self._request(self.client, url, now)
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(timeout=12.0, limits=limits, follow_redirects=False) as client:
            return await self._request(client, url, now)

    @staticmethod
    async def _request(client: httpx.AsyncClient, url: str, now: datetime) -> PtaxQuote | None:
        async with client.stream("GET", url, headers={"Accept": "application/json"}) as response:
            response.raise_for_status()
            chunks = bytearray()
            async for chunk in response.aiter_bytes():
                chunks.extend(chunk)
                if len(chunks) > 16384:
                    raise ValueError("resposta PTAX excede o limite")
        payload = json.loads(chunks)
        rows = payload.get("value") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("lista PTAX ausente")
        if not rows:
            return None
        if len(rows) != 1 or not isinstance(rows[0], dict):
            raise ValueError("resposta PTAX inesperada")
        row = rows[0]
        raw_time = row.get("dataHoraCotacao")
        if not isinstance(raw_time, str):
            raise ValueError("horário PTAX ausente")
        bulletin = datetime.fromisoformat(raw_time.replace(" ", "T"))
        if bulletin.tzinfo is None:
            bulletin = bulletin.replace(tzinfo=SAO_PAULO)
        bulletin = bulletin.astimezone(SAO_PAULO)
        if bulletin > now.astimezone(SAO_PAULO) + timedelta(minutes=5):
            raise ValueError("boletim PTAX futuro")
        if (now.astimezone(SAO_PAULO).date() - bulletin.date()).days > 7:
            raise ValueError("boletim PTAX antigo")
        quote = PtaxQuote(
            cotacaoCompra=row.get("cotacaoCompra"),
            cotacaoVenda=row.get("cotacaoVenda"),
            dataHoraBoletimIso=bulletin,
        )
        if not all(math.isfinite(x) for x in (quote.cotacaoCompra, quote.cotacaoVenda)):
            raise ValueError("valor PTAX não finito")
        if quote.cotacaoCompra > quote.cotacaoVenda:
            raise ValueError("compra PTAX superior à venda")
        return quote
