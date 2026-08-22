import uuid
from datetime import datetime
from typing import Any

from events.base import DomainEvent


class ClimaSyncRealizado(DomainEvent):
    """Evento emitido quando dados climáticos são sincronizados com sucesso."""

    event_type: str = "agricola.climatico.sync_realizado"

    unidade_produtiva_id: uuid.UUID
    provider: str
    occurred_at: datetime

    latitude: float | None = None
    longitude: float | None = None

    temperatura: float | None = None
    umidade: float | None = None
    chuva_mm: float | None = None
    vento_kmh: float | None = None
    condicao: str | None = None

    raw_payload: dict[str, Any] | None = None
    integration_job_id: uuid.UUID | None = None


class PrevisaoClimaSyncRealizado(DomainEvent):
    """Evento emitido quando as previsões climáticas são sincronizadas com sucesso."""

    event_type: str = "agricola.climatico.previsao_sync_realizado"

    unidade_produtiva_id: uuid.UUID
    provider: str
    occurred_at: datetime

    previsoes: list[dict[str, Any]]  # [{"data_previsao": "2026-08-19", "temp_max_c": 30, ...}]

    raw_payload: dict[str, Any] | None = None
    integration_job_id: uuid.UUID | None = None
