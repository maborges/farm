from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Dispositivo (estação de balança)
# ---------------------------------------------------------------------------


class DeviceCreate(BaseModel):
    nome: str = Field(..., max_length=100)
    fazenda_ids: list[uuid.UUID] = Field(..., min_length=1)
    expires_days: int = Field(default=365, ge=1, le=3650)


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
    pin_hash: str = Field(..., description="bcrypt hash do PIN da estação, gerado no cliente")
    device_fingerprint: str = Field(..., max_length=256)


class DeviceActivateResponse(BaseModel):
    device_token: str
    device_id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    fazenda_ids: list[uuid.UUID]
    expires_at: datetime


class DeviceRevokeRequest(BaseModel):
    device_id: uuid.UUID
    motivo: str | None = None


class DeviceReactivateRequest(BaseModel):
    device_id: uuid.UUID
    expires_days: int = Field(default=365, ge=1, le=3650)


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome: str
    status: str
    fazenda_ids: list[uuid.UUID]
    last_sync_at: datetime | None
    last_seen_at: datetime | None
    expires_at: datetime
    created_at: datetime


# ---------------------------------------------------------------------------
# Ordem de Pesagem — API interna consumida por outros módulos
# ---------------------------------------------------------------------------

OrigemTipo = Literal["COLHEITA", "COMPRA", "VENDA", "PECUARIA", "PESSOA", "OUTRO"]
SubjectType = Literal["VEICULO", "ANIMAL", "PESSOA"]
TipoPesagem = Literal["UNICA", "DUPLA"]


class SolicitarPesagemRequest(BaseModel):
    origem_tipo: OrigemTipo
    origem_id: uuid.UUID | None = None
    subject_type: SubjectType
    tipo_pesagem: TipoPesagem
    contexto: dict[str, Any] = Field(default_factory=dict)
    solicitado_por: uuid.UUID | None = None


class OrdemPesagemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    origem_tipo: str
    origem_id: uuid.UUID | None
    subject_type: str
    tipo_pesagem: str
    status: str
    contexto: dict[str, Any]
    dispositivo_id: uuid.UUID | None
    concluida_em: datetime | None
    cancelada_em: datetime | None
    created_at: datetime
    updated_at: datetime


class CancelarOrdemRequest(BaseModel):
    motivo: str = Field(..., min_length=3)


class PesagemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ordem_id: uuid.UUID
    numero_ticket: str
    peso_bruto_kg: Decimal | None
    peso_tara_kg: Decimal | None
    peso_liquido_kg: Decimal | None
    captured_via: str
    placa: str | None
    motorista: str | None
    animal_id: uuid.UUID | None
    pessoa_id: uuid.UUID | None
    data_entrada: datetime | None
    data_saida: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Sync Pull
# ---------------------------------------------------------------------------


class OrdemPendenteSync(BaseModel):
    id: uuid.UUID
    origem_tipo: str
    origem_id: uuid.UUID | None
    subject_type: str
    tipo_pesagem: str
    status: str
    contexto: dict[str, Any]
    created_at: datetime


class SyncTombstonesPayloadBalanca(BaseModel):
    ordens: list[str] = Field(default_factory=list)


class SyncPullResponse(BaseModel):
    sync_at: datetime
    ordens_pendentes: list[OrdemPendenteSync]
    tombstones: SyncTombstonesPayloadBalanca


# ---------------------------------------------------------------------------
# Sync Push
# ---------------------------------------------------------------------------


class SyncPushItem(BaseModel):
    local_id: str = Field(..., description="UUID gerado localmente na estação")
    operation: Literal["CREATE", "UPDATE"]
    entity_type: Literal["pesagem"]
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
    status: Literal["CREATED", "UPDATED", "CONFLICT", "ERROR"]
    server_id: str | None = None
    error_message: str | None = None


class SyncPushResponse(BaseModel):
    processed_at: datetime
    results: list[SyncPushItemResult]
