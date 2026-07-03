"""Schemas canônicos do provider OpenWeather."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OpenWeatherConfigUpsert(BaseModel):
    """Payload de criação/atualização da configuração OpenWeather."""

    api_key: str | None = Field(default=None, min_length=1, max_length=512)
    api_base_url: str = Field(default="https://api.openweathermap.org", max_length=255)
    environment: str = Field(default="production", max_length=40)
    location_query: str = Field(default="Sao Paulo,BR", min_length=1, max_length=120)
    units: str = Field(default="metric", pattern="^(metric|imperial|standard)$")
    language: str = Field(default="pt_br", max_length=10)
    timeout_seconds: int = Field(default=20, ge=5, le=120)
    cache_ttl_seconds: int = Field(default=1800, ge=60, le=86400)


class OpenWeatherConfigResponse(BaseModel):
    """Resposta mascarada da configuração OpenWeather."""

    id: int
    tenant_id: str
    provider_id: int
    provider_slug: str
    status: str
    ativo: bool
    lifecycle_state: str
    connection_payload: dict[str, Any] = Field(default_factory=dict)
    configuracoes: dict[str, Any] = Field(default_factory=dict)
    api_key_configured: bool = False
    api_key_mask: str | None = None
    credential_ref_id: int | None = None
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpenWeatherWeatherSnapshotResponse(BaseModel):
    """Snapshot atual do clima consultado no provider."""

    location: str | None = None
    temperature: float | None = None
    humidity: int | None = None
    rainfall_mm: float | None = None
    wind_speed: float | None = None
    condition: str | None = None
    units: str | None = None
    observed_at: datetime | None = None
    source: str = "openweather"
    job_id: str | None = None


class OpenWeatherTestConnectionResponse(BaseModel):
    """Resposta de teste de conexão do provider OpenWeather."""

    sucesso: bool
    mensagem: str
    weather: OpenWeatherWeatherSnapshotResponse | None = None


class OpenWeatherStatusResponse(BaseModel):
    """Status canônico do provider OpenWeather."""

    configurado: bool
    ativo: bool
    ultimo_sync: datetime | None = None
    proximo_sync: datetime | None = None
    status_conexao: str
    status_legado: str | None = None
    status_canonico: str | None = None
    status_origem: str = "canonical"
    health_origem: str = "canonical"
    config_id_canonico: int | None = None
    lifecycle_state: str | None = None
    health_status: str | None = None
    health_summary: str | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0
    features_habilitadas: list[str] = Field(default_factory=list)
    policies_resumidas: list[dict[str, str | bool | int | None]] = Field(default_factory=list)
    latest_weather: OpenWeatherWeatherSnapshotResponse | None = None


class OpenWeatherHealthResponse(BaseModel):
    """Snapshot canônico de health do provider OpenWeather."""

    configurado: bool
    origem: str = "canonical"
    status: str
    summary: str | None = None
    checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0
    details: dict[str, Any] | list[Any] | str | None = None


class OpenWeatherIntegrationJobResponse(BaseModel):
    """Execução canônica de consulta climática."""

    id: str
    tenant_id: str
    config_id: int | None = None
    feature_code: str | None = None
    job_status: str
    trigger_type: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    processados: int = 0
    sucessos: int = 0
    erros: int = 0
    correlation_id: str | None = None
    result_payload: dict[str, Any] | list[Any] | None = None
    error_payload: dict[str, Any] | list[Any] | str | None = None


class OpenWeatherTimelineItemResponse(BaseModel):
    """Item consolidado da linha do tempo operacional OpenWeather."""

    id: str
    tipo_registro: str
    origem_dado: str
    feature_code: str | None = None
    status: str
    event_type: str | None = None
    resumo: str
    occurred_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duracao_ms: float | None = None
    processados: int = 0
    sucessos: int = 0
    erros: int = 0
    correlation_id: str | None = None
    payload: dict[str, Any] | list[Any] | str | None = None


class OpenWeatherOperationalDiagnosisResponse(BaseModel):
    """Diagnóstico operacional consolidado do provider OpenWeather."""

    origem: str = "canonical"
    health_atual: str
    status_degradacao: str
    ultimo_sucesso_at: datetime | None = None
    ultima_falha_at: datetime | None = None
    falhas_consecutivas: int = 0
    feature_mais_problematica: str | None = None
    jobs_pendentes: int = 0
    jobs_falhos: int = 0
    recomendacao_operacional: str
