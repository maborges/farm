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
# Operador (login por PIN pessoal em terminal compartilhado)
# ---------------------------------------------------------------------------


class OperadorCreate(BaseModel):
    pessoa_id: uuid.UUID
    nome_exibicao: str = Field(..., max_length=150)
    pin_hash: str = Field(..., description="bcrypt hash do PIN pessoal, gerado no cliente")


class OperadorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    pessoa_id: uuid.UUID
    nome_exibicao: str
    status: str
    created_at: datetime


class OperadorAtivoResponse(BaseModel):
    """Versão pública (sem pin_hash) — consumida pela estação para montar o seletor."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nome_exibicao: str


class OperadorLoginRequest(BaseModel):
    operador_id: uuid.UUID
    pin: str = Field(..., min_length=4, description="PIN em texto puro — comparado via bcrypt no servidor")


class OperadorLoginResponse(BaseModel):
    operador_id: uuid.UUID
    pessoa_id: uuid.UUID
    nome_exibicao: str


# ---------------------------------------------------------------------------
# Ordem de Pesagem — API interna consumida por outros módulos
# ---------------------------------------------------------------------------

OrigemTipo = Literal["COLHEITA", "COMPRA", "VENDA", "PECUARIA", "PESSOA", "OUTRO"]
SubjectType = Literal["VEICULO", "ANIMAL"]
TipoPesagem = Literal["UNICA", "DUPLA", "DUPLA_ENTRADA_DESCARGA", "DUPLA_SAIDA_CARREGAMENTO"]
Etapa = Literal["UNICA", "CHEGADA", "POS_DESCARGA", "PRE_CARREGAMENTO", "SAIDA"]
ProdutoTipo = Literal["COMMODITY", "ALMOXARIFADO"]
TipoVolume = Literal["SACA", "BIG_BAG", "GRANEL", "TAMBOR", "OUTRO"]

# Etapas esperadas por tipo_pesagem, na ordem em que devem ocorrer — usado
# tanto para validar o payload do sync push quanto para saber quando o par
# está completo e o peso líquido da ordem pode ser calculado.
ETAPAS_POR_TIPO_PESAGEM: dict[str, tuple[str, ...]] = {
    "UNICA": ("UNICA",),
    "DUPLA": ("CHEGADA", "SAIDA"),
    "DUPLA_ENTRADA_DESCARGA": ("CHEGADA", "POS_DESCARGA"),
    "DUPLA_SAIDA_CARREGAMENTO": ("PRE_CARREGAMENTO", "SAIDA"),
}


class SolicitarPesagemRequest(BaseModel):
    origem_tipo: OrigemTipo
    origem_id: uuid.UUID | None = None
    subject_type: SubjectType
    tipo_pesagem: TipoPesagem
    contexto: dict[str, Any] = Field(default_factory=dict)
    solicitado_por: uuid.UUID | None = None
    produto_id: uuid.UUID | None = None
    produto_tipo: ProdutoTipo | None = None
    tipo_volume: TipoVolume | None = None
    quantidade_volumes: Decimal | None = None
    data_agendada: datetime | None = None
    numero_documento_fiscal: str | None = Field(default=None, max_length=60)


class OrdemPesagemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    origem_tipo: str
    origem_id: uuid.UUID | None
    subject_type: str
    tipo_pesagem: str
    status: str
    contexto: dict[str, Any]
    produto_id: uuid.UUID | None
    produto_tipo: str | None
    tipo_volume: str | None
    quantidade_volumes: Decimal | None
    data_agendada: datetime | None
    numero_documento_fiscal: str | None
    peso_liquido_kg: Decimal | None
    dispositivo_id: uuid.UUID | None
    concluida_em: datetime | None
    cancelada_em: datetime | None
    created_at: datetime
    updated_at: datetime


class CancelarOrdemRequest(BaseModel):
    motivo: str = Field(..., min_length=3)


class ReatribuirOrdemRequest(BaseModel):
    """Reconciliação: associa uma ordem 'OUTRO' (pesagem avulsa, sem processo
    de origem no momento da pesagem) ao processo real de outro módulo."""
    origem_tipo: OrigemTipo
    origem_id: uuid.UUID | None = None
    contexto: dict[str, Any] | None = None


class PesagemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ordem_id: uuid.UUID
    numero_ticket: str
    etapa: str
    peso_informado_kg: Decimal | None
    peso_aferido_kg: Decimal | None
    peso_tara_kg: Decimal | None
    captured_via: str
    placa: str | None
    motorista: str | None
    animal_id: uuid.UUID | None
    pessoa_id: uuid.UUID | None
    operador_pessoa_id: uuid.UUID | None
    data_pesagem: datetime | None
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
    produto_id: uuid.UUID | None
    produto_tipo: str | None
    tipo_volume: str | None
    quantidade_volumes: Decimal | None
    data_agendada: datetime | None
    numero_documento_fiscal: str | None
    etapas_realizadas: list[str] = Field(default_factory=list)
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
