from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from agricola.caderno.schemas import EventoCadernoOficialSync
from agricola.climatico.schemas import RecomendacaoOperacionalResponse


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------

class DeviceCreate(BaseModel):
    nome: str = Field(..., max_length=100)
    fazenda_ids: list[uuid.UUID] = Field(..., min_length=1)
    modulos: list[str] = Field(default=["agricola"])
    user_id: uuid.UUID
    expires_days: int = Field(default=30, ge=1, le=365)


class DeviceCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str
    activation_code: str
    activation_code_expires_at: datetime
    expires_at: datetime
    status: str


class DeviceActivateRequest(BaseModel):
    activation_code: str = Field(..., min_length=6, max_length=8)
    pin_hash: str = Field(..., description="bcrypt hash do PIN, gerado no cliente")
    device_fingerprint: str = Field(..., max_length=256)


class DeviceActivateResponse(BaseModel):
    device_token: str
    device_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_avatar_url: str | None = None
    fazenda_ids: list[uuid.UUID]
    modulos: list[str]
    expires_at: datetime


class DeviceRevokeRequest(BaseModel):
    device_id: uuid.UUID
    motivo: str | None = None


class DeviceReactivateRequest(BaseModel):
    device_id: uuid.UUID
    expires_days: int = Field(default=30, ge=1, le=365)
    motivo: str | None = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str
    status: str
    modulos: list[str]
    fazenda_ids: list[uuid.UUID]
    last_sync_at: datetime | None
    last_seen_at: datetime | None
    expires_at: datetime
    created_at: datetime


class DeviceSelfResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str
    status: str
    user_id: uuid.UUID
    user_name: str
    user_avatar_url: str | None = None
    fazenda_ids: list[uuid.UUID]
    modulos: list[str]
    expires_at: datetime


# ---------------------------------------------------------------------------
# Sync Pull
# ---------------------------------------------------------------------------

class FazendaSync(BaseModel):
    id: uuid.UUID
    nome: str
    municipio: str | None
    uf: str | None


class TalhaoSync(BaseModel):
    id: uuid.UUID
    nome: str
    unidade_produtiva_id: uuid.UUID
    area_ha: float | None
    tipo: str


class LoteSync(BaseModel):
    id: uuid.UUID
    identificacao: str
    especie: str
    quantidade_cabecas: int
    unidade_produtiva_id: uuid.UUID


class InsumoSync(BaseModel):
    id: uuid.UUID
    nome: str
    tipo: str
    unidade_medida: str | None


class SafraSync(BaseModel):
    id: uuid.UUID
    ano_safra: str
    cultura: str | None
    status: str


class TarefaPendenteSync(BaseModel):
    id: uuid.UUID
    client_id: str | None
    dispositivo_id: uuid.UUID | None
    type: str
    module: str
    status: str
    origem: str
    status_execucao: str
    titulo: str | None
    data_programada: date | None
    prioridade: str
    operador_id: uuid.UUID | None
    dados: dict[str, Any]
    unidade_produtiva_id: uuid.UUID | None
    area_rural_id: uuid.UUID | None
    lote_id: uuid.UUID | None
    client_created_at: datetime | None
    client_updated_at: datetime | None


class SyncTombstonesPayload(BaseModel):
    talhoes: list[str] = Field(default_factory=list)
    lotes: list[str] = Field(default_factory=list)
    tarefas: list[str] = Field(default_factory=list)
    insumos: list[str] = Field(default_factory=list)


class RecomendacaoOperacionalSync(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID | None
    domain: str
    status: str
    priority: str
    source_type: str
    action_type: str
    provider_name: str
    rule_code: str
    scope_type: str
    scope_id: str
    title: str
    summary: str
    rationale: str
    dedupe_key: str
    source_signal_ids: list[uuid.UUID] = Field(default_factory=list)
    confidence: float | None = None
    action_label: str | None = None
    action_target: str | None = None
    context: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    viewed_at: datetime | None = None
    accepted_at: datetime | None = None
    dismissed_at: datetime | None = None
    postponed_until: datetime | None = None
    executed_at: datetime | None = None
    superseded_at: datetime | None = None
    superseded_by_id: uuid.UUID | None = None


class SyncPullResponse(BaseModel):
    sync_at: datetime
    safras: list[SafraSync]
    fazendas: list[FazendaSync]
    talhoes: list[TalhaoSync]
    lotes: list[LoteSync]
    insumos: list[InsumoSync]
    tarefas_pendentes: list[TarefaPendenteSync]
    eventos_caderno_oficiais: list[EventoCadernoOficialSync] = Field(default_factory=list)
    recomendacoes_operacionais: list[RecomendacaoOperacionalSync] = Field(default_factory=list)
    recomendacoes_climaticas: list[RecomendacaoOperacionalResponse] = Field(default_factory=list)
    tombstones: SyncTombstonesPayload


# ---------------------------------------------------------------------------
# Sync Push
# ---------------------------------------------------------------------------

class SyncPushItem(BaseModel):
    local_id: str = Field(..., description="UUID gerado localmente")
    operation: Literal["CREATE", "UPDATE", "DELETE"]
    entity_type: str
    server_id: str | None = None
    payload: dict[str, Any]
    client_created_at: datetime
    client_updated_at: datetime


class SyncPushRequest(BaseModel):
    device_id: uuid.UUID
    last_sync_at: datetime | None = None
    items: list[SyncPushItem] = Field(..., max_length=200)


class SyncPushItemResult(BaseModel):
    local_id: str
    status: Literal["CREATED", "UPDATED", "DELETED", "CONFLICT", "ERROR"]
    server_id: str | None = None
    server_data: dict[str, Any] | None = None
    error_message: str | None = None


class SyncPushResponse(BaseModel):
    processed_at: datetime
    results: list[SyncPushItemResult]


# ---------------------------------------------------------------------------
# Tarefas Programadas (backoffice → PWA)
# ---------------------------------------------------------------------------

class TarefaProgramadaCreate(BaseModel):
    titulo: str = Field(..., max_length=200)
    type: str = Field(..., max_length=50)
    module: str = Field(default="agricola", max_length=20)
    data_programada: date
    prioridade: Literal["BAIXA", "NORMAL", "ALTA", "URGENTE"] = "NORMAL"
    unidade_produtiva_id: uuid.UUID
    area_rural_id: uuid.UUID | None = None
    lote_id: uuid.UUID | None = None
    operador_id: uuid.UUID | None = None
    dispositivo_id: uuid.UUID | None = None
    dados: dict[str, Any] = Field(default_factory=dict)


class TarefaProgramadaUpdate(BaseModel):
    titulo: str | None = Field(default=None, max_length=200)
    type: str | None = Field(default=None, max_length=50)
    module: str | None = Field(default=None, max_length=20)
    data_programada: date | None = None
    prioridade: Literal["BAIXA", "NORMAL", "ALTA", "URGENTE"] | None = None
    unidade_produtiva_id: uuid.UUID | None = None
    area_rural_id: uuid.UUID | None = None
    lote_id: uuid.UUID | None = None
    operador_id: uuid.UUID | None = None
    dispositivo_id: uuid.UUID | None = None
    dados: dict[str, Any] | None = None


class TarefaProgramadaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    titulo: str | None
    type: str
    module: str
    origem: str
    status_execucao: str
    data_programada: date | None
    prioridade: str
    operador_id: uuid.UUID | None
    dispositivo_id: uuid.UUID | None
    unidade_produtiva_id: uuid.UUID | None
    area_rural_id: uuid.UUID | None
    lote_id: uuid.UUID | None
    dados: dict[str, Any]
    fotos: list[str]
    iniciada_em: datetime | None
    concluida_em: datetime | None
    invalidado_em: datetime | None
    invalidado_por: uuid.UUID | None
    motivo_invalidacao: str | None
    created_at: datetime
    updated_at: datetime


class TarefaProgramadaInvalidarRequest(BaseModel):
    motivo: str = Field(..., min_length=10)


class ExecucaoUpdate(BaseModel):
    status_execucao: Literal["EM_EXECUCAO", "CONCLUIDA", "CANCELADA"]
    obs: str | None = None
    fotos: list[str] = Field(default_factory=list)
    localizacao_status: str = "INDISPONIVEL"
    latitude: float | None = None
    longitude: float | None = None
    client_updated_at: datetime | None = None
